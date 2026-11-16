"""표준사전 정규성 채점.

원본 노트북 "정규성 채점" (case1 행안부, case2 삼성SDS)의 진단 항목 31개를 옮긴 것이다.
각 항목은 100점 만점이고, 사전별 총점은 항목 평균, 전체 총점은 사전 4종 평균이다.
INSPC_CODE_07 만 원본과 다르다: 원본은 코드 목록과 코드값 목록 두 파일을 서로 대조하는데
여기서는 코드사전이 한 장이라, 설계 문서의 규칙(코드명+코드값 조합은 중복이 없어야 한다)으로 잰다.
"""
import re

import pandas as pd

WORD_NAME_ALLOWED = re.compile(r"[A-Z가-힣0-9+]")
WORD_ABBR_ALLOWED = re.compile(r"[A-Z0-9+]")
TERM_NAME_ALLOWED = re.compile(r"[A-Z가-힣0-9+_]")
TERM_ABBR_ALLOWED = re.compile(r"[A-Z0-9+_]")
DOMAIN_NAME_ALLOWED = re.compile(r"[A-Z가-힣0-9,+_]")

GROUPS = {"STWD": "단어", "TERM": "용어", "DOM": "도메인", "CODE": "코드"}


def _percent(passed: int, total: int) -> float:
    return round(passed / total * 100, 2) if total else 0.0


def filled(series: pd.Series):
    """빈칸 진단: 값이 들어 있는 행의 비율."""
    return int((series.astype(str) != "").sum()), len(series)


def unique(series: pd.Series):
    """중복 진단: 중복에 걸리지 않은 행의 비율. (겹친 값은 양쪽 다 감점)"""
    return int((~series.duplicated(keep=False)).sum()), len(series)


def found_in(series: pd.Series, reference, blank_passes: bool = False):
    """관계 진단: 다른 사전에서 찾을 수 있는 값의 비율.

    blank_passes: 원본은 빈칸을 '-' 로 바꿔 서로 일치시키는 방식으로 빈칸을 통과시킨다.
    """
    values = series.astype(str)
    is_found = values.isin(set(map(str, reference)))
    if blank_passes:
        is_found = is_found | (values == "")
    return int(is_found.sum()), len(series)


def well_formed(series: pd.Series, allowed: re.Pattern):
    """형식 진단: 대문자로 바꿔 허용 문자만 남겨도 원래 값과 같은 행의 비율."""
    values = series.astype(str)
    cleaned = values.map(lambda value: "".join(allowed.findall(value.upper())))
    return int((cleaned == values).sum()), len(series)


def underscore_matches_words(abbrs: pd.Series):
    """약어 형식(2): '_' 개수 + 1 이 단어 수와 같은가. 'A__B' 나 끝의 '_' 를 잡는다."""
    values = abbrs.astype(str)
    is_ok = values.map(lambda value: value.count("_") + 1 == len([w for w in value.split("_") if w]))
    return int(is_ok.sum()), len(values)


def expected_domain_name(domains: pd.DataFrame) -> pd.Series:
    scale = domains["소수점자리"].astype(str)
    length = domains["데이터길이"].astype(str) + scale.map(lambda s: f",{s}" if s not in ("", "0") else "")
    return domains["표준화된도메인분류명"].astype(str) + domains["데이터타입"].astype(str).str[:1] + length


def score_dictionaries(term_dict: pd.DataFrame, word_dict: pd.DataFrame, domain_dict: pd.DataFrame,
                       code_dict: pd.DataFrame) -> dict:
    words_in_terms = {abbr for term in term_dict["영문약어명"] for abbr in str(term).split("_")}
    word_pair = word_dict["표준단어명"].astype(str) + "_" + word_dict["단어영문약어명"].astype(str)
    code_pair = code_dict["코드명(영문)"].astype(str) + "\x1f" + code_dict["코드값"].astype(str)
    domain_matches = int((expected_domain_name(domain_dict) == domain_dict["도메인명"]).sum())

    checks = [
        ("INSPC_STWD_01", "단어 빈칸", "단어명이 비어 있지 않은가", filled(word_dict["표준단어명"])),
        ("INSPC_STWD_02", "약어 빈칸", "약어명이 비어 있지 않은가", filled(word_dict["단어영문약어명"])),
        ("INSPC_STWD_03", "단어 중복", "단어명이 중복되지 않는가", unique(word_dict["표준단어명"])),
        ("INSPC_STWD_04", "약어 중복", "약어명이 중복되지 않는가", unique(word_dict["단어영문약어명"])),
        ("INSPC_STWD_05", "단어-약어 중복", "단어명+약어명 조합이 1:1 인가", unique(word_pair)),
        ("INSPC_STWD_06", "단어-용어 관계", "단어가 용어사전에서 쓰이는가",
         found_in(word_dict["단어영문약어명"], words_in_terms)),
        ("INSPC_STWD_07", "단어-도메인분류 관계", "단어의 분류명이 도메인사전에 있는가",
         found_in(word_dict["도메인분류명"], domain_dict["표준화된도메인분류명"], blank_passes=True)),
        ("INSPC_STWD_08", "단어 형식", "한글, 영문 대문자, 숫자만 쓰는가",
         well_formed(word_dict["표준단어명"], WORD_NAME_ALLOWED)),
        ("INSPC_STWD_09", "약어 형식", "영문 대문자, 숫자만 쓰는가",
         well_formed(word_dict["단어영문약어명"], WORD_ABBR_ALLOWED)),

        ("INSPC_TERM_01", "용어 빈칸", "용어명이 비어 있지 않은가", filled(term_dict["표준용어명"])),
        ("INSPC_TERM_02", "약어 빈칸", "약어명이 비어 있지 않은가", filled(term_dict["영문약어명"])),
        ("INSPC_TERM_03", "용어-도메인 관계", "용어의 도메인명이 도메인사전에 있는가",
         found_in(term_dict["표준도메인명"], domain_dict["도메인명"])),
        ("INSPC_TERM_04", "용어 중복", "용어명이 중복되지 않는가", unique(term_dict["표준용어명"])),
        ("INSPC_TERM_05", "약어 중복", "약어명이 중복되지 않는가", unique(term_dict["영문약어명"])),
        ("INSPC_TERM_06", "용어 형식", "한글, 영문 대문자, 숫자, '_' 만 쓰는가",
         well_formed(term_dict["표준용어명"], TERM_NAME_ALLOWED)),
        ("INSPC_TERM_07", "약어 형식(1)", "영문 대문자, 숫자, '_' 만 쓰는가",
         well_formed(term_dict["영문약어명"], TERM_ABBR_ALLOWED)),
        ("INSPC_TERM_08", "약어 형식(2)", "'_' 개수 + 1 이 단어 수와 같은가",
         underscore_matches_words(term_dict["영문약어명"])),

        ("INSPC_DOM_01", "그룹명 빈칸", "도메인그룹명이 비어 있지 않은가",
         filled(domain_dict["표준도메인그룹명"])),
        ("INSPC_DOM_02", "분류명 빈칸", "도메인분류명이 비어 있지 않은가",
         filled(domain_dict["표준화된도메인분류명"])),
        ("INSPC_DOM_03", "도메인명 빈칸", "도메인명이 비어 있지 않은가", filled(domain_dict["도메인명"])),
        ("INSPC_DOM_04", "분류명-단어 관계", "분류명이 단어사전의 분류어에 있는가",
         found_in(domain_dict["표준화된도메인분류명"], word_dict["도메인분류명"])),
        ("INSPC_DOM_05", "도메인명-용어 관계", "도메인명이 용어사전에서 쓰이는가",
         found_in(domain_dict["도메인명"], term_dict["표준도메인명"])),
        ("INSPC_DOM_06", "도메인명 형식(1)", "한글, 영문 대문자, 숫자, ',' 만 쓰는가",
         well_formed(domain_dict["도메인명"], DOMAIN_NAME_ALLOWED)),
        ("INSPC_DOM_07", "도메인명 형식(2)", "분류명 + 타입 첫 글자 + 길이 조합과 같은가",
         (domain_matches, len(domain_dict))),

        ("INSPC_CODE_01", "코드영문명 빈칸", "코드영문명이 비어 있지 않은가", filled(code_dict["코드명(영문)"])),
        ("INSPC_CODE_02", "코드한글명 빈칸", "코드한글명이 비어 있지 않은가", filled(code_dict["코드명(한글)"])),
        ("INSPC_CODE_03", "코드값 빈칸", "코드값이 비어 있지 않은가", filled(code_dict["코드값"])),
        ("INSPC_CODE_04", "코드값의미 빈칸", "코드값의미가 비어 있지 않은가", filled(code_dict["코드값의미"])),
        ("INSPC_CODE_05", "한글코드명-용어 관계", "코드한글명이 용어사전에 있는가",
         found_in(code_dict["코드명(한글)"], term_dict["표준용어명"])),
        ("INSPC_CODE_06", "영문코드명-용어 관계", "코드영문명이 용어사전에 있는가",
         found_in(code_dict["코드명(영문)"], term_dict["영문약어명"])),
        ("INSPC_CODE_07", "코드명-코드값 중복", "코드명+코드값 조합이 중복되지 않는가", unique(code_pair)),
    ]

    items = [
        {"code": code, "group": GROUPS[code.split("_")[1]], "title": title, "rule": rule,
         "passed": passed, "total": total, "score": _percent(passed, total)}
        for code, title, rule, (passed, total) in checks
    ]
    totals = {
        group: round(sum(i["score"] for i in items if i["group"] == group)
                     / len([i for i in items if i["group"] == group]), 2)
        for group in GROUPS.values()
    }
    return {"items": items, "totals": totals, "overall": round(sum(totals.values()) / len(totals), 2)}
