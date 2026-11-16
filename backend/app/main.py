"""포트폴리오 API. 표준화 파이프라인을 실제로 실행하고 결과를 Postgres 에 남긴다."""
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import db
from .pipeline import run_pipeline, trace_term
from .scoring import score_dictionaries

logger = logging.getLogger("portfolio")
# 공개 사이트에서 실행 버튼 연타로 DB 가 바빠지지 않게, 방금 돌린 결과는 그대로 돌려준다
RERUN_COOLDOWN = timedelta(seconds=3)

COLUMN_LABELS = {
    "table_physical": "테이블물리명", "table_korean": "테이블한글명", "column_physical": "컬럼물리명",
    "column_fullname": "컬럼물리명FullName", "column_korean": "컬럼한글명", "domain_group": "표준도메인그룹명",
    "domain_class": "도메인분류명", "data_type": "데이터타입", "data_length": "데이터길이", "data_scale": "소수점자리",
}
CODE_LABELS = {
    "code_korean": "코드명(한글)", "code_english": "코드명(영문)", "code_fullname": "코드영문명 FullName",
    "data_type": "데이터타입", "data_length": "데이터길이", "code_value": "코드값", "code_meaning": "코드값의미",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.wait_for_database()
    db.init_database()
    yield


router = APIRouter(prefix="/api")


class TryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    data_type: Literal["CHAR", "VARCHAR2", "NUMBER", "DATE"] = "VARCHAR2"
    data_length: int = Field(default=10, ge=1, le=4000)
    data_scale: int = Field(default=0, ge=0, le=38)


def _table(frame, labels: dict) -> dict:
    return {"columns": list(labels.values()), "rows": frame[list(labels)].astype(str).values.tolist()}


def _execute_run() -> dict:
    started = time.perf_counter()
    columns, codes, dictionary = db.load_inputs()
    result = run_pipeline(columns, codes, dictionary)
    outputs = result.outputs
    scores = score_dictionaries(outputs["term_dict"], outputs["word_dict"], outputs["domain_dict"],
                                outputs["code_dict"])
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    db.save_run(elapsed_ms, result.steps, scores, result.unknown_words, outputs)
    return db.latest_run()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/input")
def get_input():
    columns, codes, dictionary = db.load_inputs()
    return {
        "columns": _table(columns, COLUMN_LABELS),
        "codes": _table(codes, CODE_LABELS),
        "word_count": len(dictionary),
    }


@router.get("/runs/latest")
def get_latest_run():
    run = db.latest_run()
    if run is None:
        raise HTTPException(status_code=404, detail="아직 실행한 적이 없습니다. 먼저 실행해 주세요.")
    return run


@router.post("/runs")
def create_run():
    latest = db.latest_run()
    if latest is not None:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(latest["created_at"])
        if age < RERUN_COOLDOWN:
            return latest
    try:
        return _execute_run()
    except Exception:
        logger.exception("파이프라인 실행 실패")
        raise HTTPException(status_code=500, detail="파이프라인 실행에 실패했습니다. 잠시 뒤 다시 시도해 주세요.")


@router.post("/try")
def try_term(request: TryRequest):
    _, _, dictionary = db.load_inputs()
    return trace_term(request.name, request.data_type, request.data_length, request.data_scale, dictionary)


def create_app() -> FastAPI:
    application = FastAPI(title="Portfolio API", lifespan=lifespan)
    application.include_router(router)
    return application


app = create_app()
