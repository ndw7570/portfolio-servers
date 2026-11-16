"""메타데이터 표준화 파이프라인.

원본 노트북 "메타데이터 사전 자동 전처리 프로세스(표준화)"의 로직을 함수로 옮긴 것이다.
노트북은 globals() 동적 변수와 엑셀 파일에 의존해서 서버에서 그대로 돌릴 수 없다.
처리 규칙(정규식, 분리, 사전 대입, 도메인명 조합)은 원본과 같게 유지한다.
"""
import re
from dataclasses import dataclass, field

import pandas as pd

# 원본 정규식 그대로다. '+' 는 문자 클래스 안이라 "더하기 기호 허용"으로 동작한다
ENG_ALLOWED = re.compile(r"[A-Z0-9_+]")
HANGUL = re.compile(r"[가-힣]")
DIGITS = re.compile(r"[0-9]")
LATIN = re.compile(r"[a-zA-Z]")

CLASS_FOR_DIGITS_ONLY = "수"
CLASS_FOR_NO_HANGUL = "기타"
UNKNOWN_WORD = ""


@dataclass
class PipelineResult:
    steps: list = field(default_factory=list)
    outputs: dict = field(default_factory=dict)
    unknown_words: list = field(default_factory=list)


def clean_english_name(name: str) -> str:
    """대문자로 바꾼 뒤 허용 문자만 남긴다."""
    return "".join(ENG_ALLOWED.findall(str(name).upper()))


def split_valid_names(frame: pd.DataFrame, column: str):
    """이름이 규칙에 맞는 행과 어긋난 행을 가른다.

    원본은 어긋난 행이 하나라도 있으면 예외로 멈추고 사람이 고친다.
    웹에서는 멈출 수 없으니 어긋난 행을 따로 돌려준다.
    """
    cleaned = frame[column].map(clean_english_name)
    is_valid = (cleaned == frame[column]) & (cleaned != "")
    return frame[is_valid].reset_index(drop=True), frame[~is_valid].reset_index(drop=True)


def split_tokens(names: pd.Series) -> pd.DataFrame:
    """'_' 기준으로 쪼개 (용어 순번, 단어 순서, 약어) 긴 표로 만든다."""
    rows = [
        {"term_idx": term_idx, "ord": order, "abbr": abbr}
        for term_idx, name in enumerate(names)
        for order, abbr in enumerate(str(name).split("_"))
        if abbr != ""
    ]
    return pd.DataFrame(rows, columns=["term_idx", "ord", "abbr"])


def build_word_list(col_tokens: pd.DataFrame, code_tokens: pd.DataFrame, col_names: pd.Series,
                    code_names: pd.Series, dictionary: dict) -> pd.DataFrame:
    """컬럼과 코드의 단어를 합쳐 중복을 없애고 사전에서 한글명을 찾는다.

    순서는 원본과 같다: 컬럼 쪽 단어가 먼저, 각 그룹 안에서는 단어 순서(ord) 우선.
    """
    parts = []
    for tokens, names, kind in ((col_tokens, col_names, "COL"), (code_tokens, code_names, "CODE")):
        first_seen = tokens.sort_values(["ord", "term_idx"], kind="stable").drop_duplicates("abbr")
        part = first_seen.assign(dvsn=kind, example=first_seen["term_idx"].map(names.__getitem__))
        parts.append(part[["abbr", "dvsn", "example"]])
    words = pd.concat(parts).drop_duplicates("abbr").reset_index(drop=True)
    words["name"] = words["abbr"].map(lambda abbr: dictionary.get(abbr, UNKNOWN_WORD))
    return words


def compose_terms(tokens: pd.DataFrame, names: pd.Series, words: pd.DataFrame) -> pd.DataFrame:
    """쪼갠 단어에 한글명을 대입한 뒤 다시 이어 TO-BE 용어명을 만든다."""
    name_of = dict(zip(words["abbr"], words["name"]))
    index_of = {abbr: position for position, abbr in enumerate(words["abbr"])}
    rows = []
    for term_idx, name in enumerate(names):
        abbrs = tokens.loc[tokens["term_idx"] == term_idx].sort_values("ord")["abbr"].tolist()
        rows.append({
            "eng": "_".join(abbrs),
            "kor": "".join(name_of[abbr] for abbr in abbrs),
            "abbrs": abbrs,
            "kor_words": [name_of[abbr] for abbr in abbrs],
            "word_ids": [index_of[abbr] for abbr in abbrs],
            "source": name,
        })
    return pd.DataFrame(rows, columns=["eng", "kor", "abbrs", "kor_words", "word_ids", "source"])


def normalize_domain_class(value: str) -> str:
    """도메인 분류명은 한글만 허용한다. (원본 col_dom_emoti_rmv 의 'not_num' 분기)

    숫자뿐이면 '수', 한글이 하나도 없으면 '기타', 섞여 있으면 한글만 남긴다.
    """
    text = str(value)
    hangul = "".join(HANGUL.findall(text))
    if text == hangul:
        return text
    if text != "" and text == "".join(DIGITS.findall(text)):
        return CLASS_FOR_DIGITS_ONLY
    if hangul == "":
        return CLASS_FOR_NO_HANGUL
    return hangul


def domain_length(length, scale) -> str:
    """길이는 숫자만 남기고, 소수점자리가 0 이나 빈 값이면 생략한다."""
    digits = "".join(DIGITS.findall(str(length)))
    scale_text = "".join(DIGITS.findall(str(scale)))
    if scale_text in ("", "0"):
        return digits
    return f"{digits},{scale_text}"


def domain_name(domain_class: str, data_type: str, length, scale) -> str:
    """도메인명 = 분류명 + 데이터타입 첫 글자 + 길이[,소수점자리]. 예: 번호 + CHAR + 7 -> 번호C7"""
    return f"{domain_class}{str(data_type)[:1]}{domain_length(length, scale)}"


def attach_domain(terms: pd.DataFrame, data_type: pd.Series, length: pd.Series, scale: pd.Series) -> pd.DataFrame:
    """용어의 마지막 단어를 분류어로 삼아 도메인명을 붙인다."""
    out = terms.copy()
    out["class_abbr"] = out["abbrs"].map(lambda abbrs: abbrs[-1] if abbrs else "")
    out["class_raw"] = out["kor_words"].map(lambda words: words[-1] if words else "")
    out["class"] = out["class_raw"].map(normalize_domain_class)
    out["data_type"] = data_type.values
    out["data_length"] = [("".join(DIGITS.findall(str(v)))) for v in length.values]
    out["data_scale"] = ["" if str(v) in ("", "0") else str(v) for v in scale.values]
    out["domain"] = [
        domain_name(c, t, l, s)
        for c, t, l, s in zip(out["class"], out["data_type"], out["data_length"], out["data_scale"])
    ]
    return out


def trace_term(name: str, data_type: str, length, scale, dictionary: dict) -> dict:
    """이름 하나가 단계별로 어떻게 바뀌는지 보여 준다. (직접 해보기용)"""
    cleaned = clean_english_name(name)
    abbrs = [abbr for abbr in cleaned.split("_") if abbr != ""]
    words = [{"abbr": abbr, "name": dictionary.get(abbr, UNKNOWN_WORD)} for abbr in abbrs]
    is_complete = bool(words) and all(word["name"] != UNKNOWN_WORD for word in words)
    class_raw = words[-1]["name"] if words else ""
    domain_class = normalize_domain_class(class_raw) if is_complete else ""
    return {
        "input": name,
        "cleaned": cleaned,
        "removed": cleaned != str(name),
        "words": words,
        "term_eng": "_".join(abbrs),
        "term_kor": "".join(word["name"] for word in words) if is_complete else "",
        "domain_class": domain_class,
        "domain": domain_name(domain_class, data_type, length, scale) if is_complete else "",
        "is_complete": is_complete,
    }


def _mapping(terms: pd.DataFrame, eng_label: str, kor_label: str) -> pd.DataFrame:
    width = max((len(ids) for ids in terms["word_ids"]), default=0)
    out = pd.DataFrame({eng_label: terms["eng"], kor_label: terms["kor"]})
    for position in range(width):
        out[f"단어{position}"] = terms["word_ids"].map(
            lambda ids, p=position: str(ids[p]) if p < len(ids) else "")
    return out


def run_pipeline(columns: pd.DataFrame, codes: pd.DataFrame, dictionary: dict) -> PipelineResult:
    """테이블컬럼정의서와 코드사전을 받아 사전 4종과 정의서, 매핑정보를 만든다."""
    result = PipelineResult()

    # 1. 형태 점검
    columns_ok, columns_bad = split_valid_names(columns, "column_physical")
    codes_ok, codes_bad = split_valid_names(codes, "code_english")
    result.steps.append({
        "title": "영문명 형태 점검",
        "detail": "대문자, 숫자, '_' 외의 글자가 있는 이름을 걸러 낸다.",
        "metrics": {"컬럼 행": len(columns), "코드 행": len(codes),
                    "규칙 위반": len(columns_bad) + len(codes_bad)},
    })

    # 2. 단어 분리
    col_tokens = split_tokens(columns_ok["column_physical"])
    code_tokens = split_tokens(codes_ok["code_english"])
    result.steps.append({
        "title": "'_' 기준 단어 분리",
        "detail": "BS_PLN_NO 를 BS / PLN / NO 로 쪼갠다.",
        "metrics": {"컬럼에서 나온 단어": len(col_tokens), "코드에서 나온 단어": len(code_tokens)},
    })

    # 3. 중복 제거 + 사전 대입
    words = build_word_list(col_tokens, code_tokens, columns_ok["column_physical"],
                            codes_ok["code_english"], dictionary)
    result.unknown_words = words.loc[words["name"] == UNKNOWN_WORD, "abbr"].tolist()
    result.steps.append({
        "title": "중복 제거와 사전 대입",
        "detail": "고유 단어만 남기고 누적사전에서 한글명을 찾는다.",
        "metrics": {"고유 단어": len(words), "사전에 없는 단어": len(result.unknown_words)},
    })

    # 4. 용어 재조합
    col_terms = compose_terms(col_tokens, columns_ok["column_physical"], words)
    code_terms = compose_terms(code_tokens, codes_ok["code_english"], words)
    renamed = int((col_terms["kor"] != columns_ok["column_korean"]).sum())
    result.steps.append({
        "title": "용어명 재조합",
        "detail": "단어 한글명을 다시 이어 표준 용어명(TO-BE)을 만든다.",
        "metrics": {"컬럼 용어": len(col_terms), "한글명이 바뀐 컬럼": renamed},
    })

    # 5. 도메인명 생성
    col_terms = attach_domain(col_terms, columns_ok["data_type"], columns_ok["data_length"],
                              columns_ok["data_scale"])
    code_scale = pd.Series([""] * len(codes_ok), dtype=object)
    code_terms = attach_domain(code_terms, codes_ok["data_type"], codes_ok["data_length"], code_scale)
    all_domains = pd.concat([col_terms["domain"], code_terms["domain"]])
    result.steps.append({
        "title": "도메인명 생성",
        "detail": "분류어 + 데이터타입 첫 글자 + 길이. 예: 번호 + CHAR + 7 = 번호C7",
        "metrics": {"고유 도메인": int(all_domains.nunique())},
    })

    # 6. 산출물
    col_terms = col_terms.assign(dvsn="COL", fullname=columns_ok["column_fullname"].values,
                                 group=columns_ok["domain_group"].values,
                                 class_input=columns_ok["domain_class"].values)
    code_terms = code_terms.assign(dvsn="CODE", fullname=codes_ok["code_fullname"].values,
                                   group="", class_input="")
    all_terms = pd.concat([col_terms, code_terms], ignore_index=True)

    unique_terms = all_terms.drop_duplicates("eng")
    term_dict = pd.DataFrame({
        "표준용어명": unique_terms["kor"], "영문약어명": unique_terms["eng"],
        "영문FullName": unique_terms["fullname"], "표준도메인명": unique_terms["domain"],
        "표준코드명": unique_terms["eng"].where(unique_terms["dvsn"] == "CODE", ""),
        "구분": unique_terms["dvsn"],
    }).reset_index(drop=True)

    class_abbrs = set(all_terms["class_abbr"])
    is_class_word = words["abbr"].isin(class_abbrs)
    word_dict = pd.DataFrame({
        "표준단어명": words["name"], "단어영문약어명": words["abbr"],
        "형식단어여부": is_class_word.map({True: "Y", False: ""}),
        "도메인분류명": words["name"].where(is_class_word, ""),
        "구분": words["dvsn"], "사용예시": words["example"],
    })

    unique_domains = all_terms.drop_duplicates("domain")
    domain_dict = pd.DataFrame({
        "표준도메인그룹명": unique_domains["group"], "도메인분류명": unique_domains["class_input"],
        "표준화된도메인분류명": unique_domains["class"], "도메인명": unique_domains["domain"],
        "데이터타입": unique_domains["data_type"], "데이터길이": unique_domains["data_length"],
        "소수점자리": unique_domains["data_scale"], "구분": unique_domains["dvsn"],
    }).reset_index(drop=True)

    code_dict = pd.DataFrame({
        "코드명(영문)": code_terms["eng"], "코드명(한글)": code_terms["kor"],
        "데이터타입": codes_ok["data_type"], "데이터길이": codes_ok["data_length"],
        "코드값": codes_ok["code_value"], "코드값의미": codes_ok["code_meaning"],
        "코드값설명": codes_ok["code_desc"],
    }).drop_duplicates(["코드명(영문)", "코드명(한글)", "코드값"]).reset_index(drop=True)

    column_definition = pd.DataFrame({
        "테이블물리명": columns_ok["table_physical"], "테이블한글명": columns_ok["table_korean"],
        "컬럼물리명": columns_ok["column_physical"],
        "컬럼한글명(AS-IS)": columns_ok["column_korean"], "컬럼한글명(TO-BE)": col_terms["kor"],
        "변경": (col_terms["kor"] != columns_ok["column_korean"]).map({True: "변경", False: ""}),
        "도메인명": col_terms["domain"], "데이터타입": columns_ok["data_type"],
        "데이터길이": columns_ok["data_length"], "소수점자리": col_terms["data_scale"],
    })

    code_definition = pd.DataFrame({
        "코드명(영문)": codes_ok["code_english"],
        "코드명(한글)(AS-IS)": codes_ok["code_korean"], "코드명(한글)(TO-BE)": code_terms["kor"],
        "변경": (code_terms["kor"] != codes_ok["code_korean"]).map({True: "변경", False: ""}),
        "코드값": codes_ok["code_value"], "코드값의미": codes_ok["code_meaning"],
    })

    result.outputs = {
        "term_dict": term_dict, "word_dict": word_dict, "domain_dict": domain_dict, "code_dict": code_dict,
        "column_definition": column_definition, "code_definition": code_definition,
        "term_mapping": _mapping(col_terms, "용어영문약어명", "용어명"),
        "code_mapping": _mapping(code_terms.drop_duplicates("eng"), "영문코드명", "한글코드명"),
        "rejected": pd.DataFrame({
            "구분": ["COL"] * len(columns_bad) + ["CODE"] * len(codes_bad),
            "이름": columns_bad["column_physical"].tolist() + codes_bad["code_english"].tolist(),
        }),
    }
    result.steps.append({
        "title": "산출물 생성",
        "detail": "사전 4종, 정의서 2종(AS-IS / TO-BE), 매핑정보 2종을 만든다.",
        "metrics": {"용어": len(term_dict), "단어": len(word_dict), "도메인": len(domain_dict),
                    "코드": len(code_dict)},
    })
    return result
