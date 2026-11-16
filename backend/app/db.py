"""Postgres 접근. 입력 샘플과 사전은 표로, 실행 결과는 JSONB 로 둔다."""
import json
import os
import time
from pathlib import Path

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

SEED_DIR = Path(__file__).parent / "seed"
# 공개 사이트라 누구나 실행 버튼을 누를 수 있다. 쌓이지 않게 최근 것만 남긴다
RUNS_TO_KEEP = 5
CONNECT_RETRIES = 30
CONNECT_RETRY_SECONDS = 2

COLUMN_FIELDS = ["dept_code", "dept_name", "system_name", "db_name", "table_physical", "table_korean",
                 "column_physical", "column_fullname", "column_korean", "domain_group", "domain_class",
                 "data_type", "data_length", "data_scale"]
CODE_FIELDS = ["dept_code", "dept_name", "code_korean", "code_english", "code_fullname", "data_type",
               "data_length", "code_value", "code_meaning", "code_desc"]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS src_column_def (
    id serial PRIMARY KEY, {", ".join(f"{name} text NOT NULL DEFAULT ''" for name in COLUMN_FIELDS)});
CREATE TABLE IF NOT EXISTS src_code_def (
    id serial PRIMARY KEY, {", ".join(f"{name} text NOT NULL DEFAULT ''" for name in CODE_FIELDS)});
CREATE TABLE IF NOT EXISTS std_word (abbr text PRIMARY KEY, name text NOT NULL);
CREATE TABLE IF NOT EXISTS pipeline_run (
    id serial PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT now(), elapsed_ms integer NOT NULL,
    steps jsonb NOT NULL, scores jsonb NOT NULL, unknown_words jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS pipeline_output (
    run_id integer NOT NULL REFERENCES pipeline_run(id) ON DELETE CASCADE, name text NOT NULL,
    columns jsonb NOT NULL, rows jsonb NOT NULL, PRIMARY KEY (run_id, name));
"""


def connect() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 환경변수가 필요합니다.")
    return psycopg.connect(url, row_factory=dict_row)


def wait_for_database() -> None:
    """compose 의 healthcheck 가 있어도 첫 연결은 실패할 수 있어 잠깐 기다린다."""
    for attempt in range(CONNECT_RETRIES):
        try:
            with connect():
                return
        except psycopg.OperationalError:
            if attempt == CONNECT_RETRIES - 1:
                raise
            time.sleep(CONNECT_RETRY_SECONDS)


def _load_seed(name: str) -> list:
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def _insert_all(cur, table: str, fields: list, rows: list) -> None:
    placeholders = ", ".join(["%s"] * len(fields))
    cur.executemany(f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({placeholders})",
                    [[row.get(name, "") for name in fields] for row in rows])


def init_database() -> None:
    """표를 만들고, 비어 있으면 샘플을 넣는다."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute("SELECT count(*) AS n FROM src_column_def")
        if cur.fetchone()["n"] == 0:
            _insert_all(cur, "src_column_def", COLUMN_FIELDS, _load_seed("columns.json"))
            _insert_all(cur, "src_code_def", CODE_FIELDS, _load_seed("codes.json"))
            _insert_all(cur, "std_word", ["abbr", "name"], _load_seed("words.json"))


def _frame(cur, sql: str, fields: list) -> pd.DataFrame:
    cur.execute(sql)
    return pd.DataFrame(cur.fetchall(), columns=fields)


def load_inputs():
    with connect() as conn, conn.cursor() as cur:
        columns = _frame(cur, f"SELECT {', '.join(COLUMN_FIELDS)} FROM src_column_def ORDER BY id", COLUMN_FIELDS)
        codes = _frame(cur, f"SELECT {', '.join(CODE_FIELDS)} FROM src_code_def ORDER BY id", CODE_FIELDS)
        cur.execute("SELECT abbr, name FROM std_word ORDER BY abbr")
        dictionary = {row["abbr"]: row["name"] for row in cur.fetchall()}
    return columns, codes, dictionary


def save_run(elapsed_ms: int, steps: list, scores: dict, unknown_words: list, outputs: dict) -> int:
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_run (elapsed_ms, steps, scores, unknown_words) VALUES (%s, %s, %s, %s) RETURNING id",
            (elapsed_ms, Jsonb(steps), Jsonb(scores), Jsonb(unknown_words)))
        run_id = cur.fetchone()["id"]
        for name, frame in outputs.items():
            cur.execute("INSERT INTO pipeline_output (run_id, name, columns, rows) VALUES (%s, %s, %s, %s)",
                        (run_id, name, Jsonb(list(frame.columns)), Jsonb(frame.astype(str).values.tolist())))
        cur.execute("DELETE FROM pipeline_run WHERE id NOT IN (SELECT id FROM pipeline_run ORDER BY id DESC LIMIT %s)",
                    (RUNS_TO_KEEP,))
    return run_id


def latest_run():
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM pipeline_run ORDER BY id DESC LIMIT 1")
        run = cur.fetchone()
        if run is None:
            return None
        cur.execute("SELECT name, columns, rows FROM pipeline_output WHERE run_id = %s", (run["id"],))
        run["outputs"] = {row["name"]: {"columns": row["columns"], "rows": row["rows"]} for row in cur.fetchall()}
    run["created_at"] = run["created_at"].isoformat()
    return run
