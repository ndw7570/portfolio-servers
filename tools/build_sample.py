"""원본 엑셀/PDF에서 공개용 샘플(seed JSON, 문서 이미지)을 만든다.

원본은 저장소에 넣지 않는다 - 실제 부서코드, 시스템명, 협력업체명이 들어 있어서다.
그래서 이 스크립트가 "무엇을 뽑고 무엇을 가렸는지"의 유일한 기록이다.

사용: python tools/build_sample.py <원본 01 폴더 경로> [--docs]
(--docs 는 pymupdf 가 필요하다)
"""
import glob
import json
import os
import sys

from xlsx_reader import sheets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_DIR = os.path.join(ROOT, "backend", "app", "seed")
DOCS_DIR = os.path.join(ROOT, "frontend", "public", "docs")

# 가리는 값: 조직과 시스템을 특정할 수 있는 식별자
MASK = {"dept_code": "00000000", "dept_name": "운영부서", "system_name": "샘플시스템", "db_name": "SAMPLEDB"}
# 테이블별로 가져올 행 수 (None = 전부). 맛보기라 4개 테이블만 쓴다
TABLE_PICK = {"TB_DB013": None, "TB_DB001": 20, "TB_SZ001": None, "TB_SZ003": None}
# 회사명, 인사 정보가 없는 코드만 고른다
CODE_PICK = ["EDU_DV_CD", "EDU_KND_CD", "CREW_WRK_JOB_TP_CD", "DIA_APL_STT_CD", "WRK_ITST_CD",
             "CRW_LCNS_INFO_CD", "PJT_DIA_CHG_DV_CD", "APRV_REQ_DV_CD", "PTRN_DV_CD"]
# 문서별로 공개할 쪽 (0부터). 전부가 아니라 핵심 쪽만 보여 준다
DOC_PAGES = {
    "process": ("표준화 프로세스 정리.pdf", [1, 7, 10, 12, 16]),
    "design": ("표준화 설계(개인검토).pdf", [2, 3, 4, 16]),
    "criteria": ("참고1) 표준화 점검 기준(남덕우 개발).pdf", [0, 1, 2]),
    "pmss": ("참고2) 표준화 점검 기준 개발 과정(남덕우 개발).pdf", [0, 1, 3]),
}


def find(src, name):
    hits = glob.glob(os.path.join(src, "**", name), recursive=True)
    if not hits:
        raise SystemExit(f"원본에서 찾지 못함: {name}")
    return hits[0]


def cell(row, i):
    return row[i].strip() if i < len(row) else ""


def build_columns(rows):
    out, taken = [], {}
    for r in rows:
        table = cell(r, 5)
        if table not in TABLE_PICK:
            continue
        limit = TABLE_PICK[table]
        if limit is not None and taken.get(table, 0) >= limit:
            continue
        taken[table] = taken.get(table, 0) + 1
        table_alias = "TB_SAMPLE%02d" % (list(TABLE_PICK).index(table) + 1)
        out.append({
            **MASK, "table_physical": table_alias, "table_korean": cell(r, 6),
            "column_physical": cell(r, 7), "column_fullname": cell(r, 8), "column_korean": cell(r, 9),
            "domain_group": cell(r, 11), "domain_class": cell(r, 12),
            "data_type": cell(r, 13), "data_length": cell(r, 14), "data_scale": cell(r, 15),
        })
    return out


def build_codes(rows):
    return [{
        "dept_code": MASK["dept_code"], "dept_name": MASK["dept_name"],
        "code_korean": cell(r, 2), "code_english": cell(r, 4), "code_fullname": cell(r, 6),
        "data_type": cell(r, 7), "data_length": cell(r, 8),
        "code_value": cell(r, 10), "code_meaning": cell(r, 11), "code_desc": cell(r, 12),
    } for r in rows if cell(r, 4) in CODE_PICK]


def build_words(rows):
    # 원본 누적사전(8,774행)은 서버에 없어서, 산출물의 표준단어사전을 사전으로 쓴다
    return [{"abbr": cell(r, 3), "name": cell(r, 1)} for r in rows if cell(r, 3)]


def write(name, data):
    with open(os.path.join(SEED_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"{name}: {len(data)}")


def render_docs(src):
    import pymupdf
    for key, (pdf, pages) in DOC_PAGES.items():
        doc = pymupdf.open(find(src, pdf))
        for n, page in enumerate(pages, 1):
            doc[page].get_pixmap(dpi=110).save(os.path.join(DOCS_DIR, f"{key}-{n}.png"))
        print(f"{key}: {len(pages)}쪽 / 전체 {len(doc)}쪽")


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = sys.argv[1]
    inp = sheets(find(src, "input_ver0.1.xlsx"))
    write("columns.json", build_columns(inp["1. 테이블컬럼정의서_ 요청"][3:]))
    write("codes.json", build_codes(inp["3. 코드사전_요청"][3:]))
    write("words.json", build_words(sheets(find(src, "DICT_ver0.1_250903_18.xlsx"))["표준단어사전"][1:]))
    if "--docs" in sys.argv:
        render_docs(src)


if __name__ == "__main__":
    main()
