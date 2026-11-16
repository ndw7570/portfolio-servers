import json
from pathlib import Path

import pandas as pd
import pytest

from app.pipeline import (clean_english_name, domain_name, normalize_domain_class, run_pipeline,
                          split_tokens, split_valid_names, trace_term)
from app.scoring import score_dictionaries

SEED = Path(__file__).parent.parent / "app" / "seed"
DICTIONARY = {"BS": "기본", "PLN": "계획", "NO": "번호", "TRN": "열차", "ID": "ID", "RGTR": "등록자",
              "EDU": "교육", "DV": "구분", "CD": "코드"}


def make_columns(rows):
    base = {"table_physical": "T1", "table_korean": "표", "column_fullname": "", "domain_group": "번호",
            "domain_class": "번호", "data_scale": ""}
    return pd.DataFrame([{**base, **row} for row in rows])


def make_codes(rows):
    base = {"code_fullname": "", "data_type": "VARCHAR2", "data_length": "2", "code_desc": ""}
    return pd.DataFrame([{**base, **row} for row in rows])


@pytest.fixture
def small_result():
    columns = make_columns([
        {"column_physical": "BS_PLN_NO", "column_korean": "기본계획넘버", "data_type": "CHAR", "data_length": "7"},
        {"column_physical": "TRN_NO", "column_korean": "열차번호", "data_type": "CHAR", "data_length": "5"},
        {"column_physical": "RGTR_ID", "column_korean": "등록자ID", "data_type": "VARCHAR2", "data_length": "6"},
    ])
    codes = make_codes([
        {"code_english": "EDU_DV_CD", "code_korean": "교육_구분_코드", "code_value": "01", "code_meaning": "직무교육"},
        {"code_english": "EDU_DV_CD", "code_korean": "교육_구분_코드", "code_value": "02", "code_meaning": "전문교육"},
    ])
    return run_pipeline(columns, codes, DICTIONARY)


def test_clean_english_name_uppercases_and_drops_disallowed_characters():
    assert clean_english_name("bs-pln no!") == "BSPLNNO"


def test_split_valid_names_separates_rows_that_break_the_naming_rule():
    frame = pd.DataFrame({"name": ["TRN_NO", "trn no", ""]})

    valid, rejected = split_valid_names(frame, "name")

    assert valid["name"].tolist() == ["TRN_NO"]
    assert rejected["name"].tolist() == ["trn no", ""]


def test_split_tokens_keeps_term_index_and_word_order():
    tokens = split_tokens(pd.Series(["BS_PLN_NO", "TRN_NO"]))

    assert tokens.values.tolist() == [[0, 0, "BS"], [0, 1, "PLN"], [0, 2, "NO"], [1, 0, "TRN"], [1, 1, "NO"]]


@pytest.mark.parametrize("raw, expected", [
    ("번호", "번호"), ("123", "수"), ("ID", "기타"), ("코드8", "코드"), ("코드AA", "코드"), ("SNS8", "기타"),
])
def test_normalize_domain_class_allows_only_hangul(raw, expected):
    assert normalize_domain_class(raw) == expected


@pytest.mark.parametrize("scale, expected", [("", "순서N22"), ("0", "순서N22"), ("4", "순서N22,4")])
def test_domain_name_appends_scale_only_when_non_zero(scale, expected):
    assert domain_name("순서", "NUMBER", "22", scale) == expected


def test_pipeline_recombines_korean_term_from_dictionary_words(small_result):
    definition = small_result.outputs["column_definition"]

    assert definition["컬럼한글명(TO-BE)"].tolist() == ["기본계획번호", "열차번호", "등록자ID"]
    assert definition["변경"].tolist() == ["변경", "", ""]


def test_pipeline_builds_domain_name_from_last_word(small_result):
    assert small_result.outputs["column_definition"]["도메인명"].tolist() == ["번호C7", "번호C5", "기타V6"]


def test_pipeline_word_dictionary_is_unique_and_marks_class_words(small_result):
    words = small_result.outputs["word_dict"]

    assert words["단어영문약어명"].is_unique
    assert words.loc[words["형식단어여부"] == "Y", "단어영문약어명"].tolist() == ["NO", "ID", "CD"]


def test_pipeline_mapping_points_to_word_dictionary_rows(small_result):
    words = small_result.outputs["word_dict"]["단어영문약어명"].tolist()
    first = small_result.outputs["term_mapping"].iloc[0]

    assert [words[int(first[f"단어{i}"])] for i in range(3)] == ["BS", "PLN", "NO"]


def test_pipeline_code_dictionary_strips_underscores_from_korean_name(small_result):
    codes = small_result.outputs["code_dict"]

    assert codes["코드명(한글)"].unique().tolist() == ["교육구분코드"]
    assert len(codes) == 2


def test_pipeline_reports_words_missing_from_dictionary():
    columns = make_columns([{"column_physical": "XYZ_NO", "column_korean": "미상번호", "data_type": "CHAR",
                             "data_length": "3"}])

    result = run_pipeline(columns, make_codes([]).reindex(columns=[
        "code_english", "code_korean", "code_fullname", "data_type", "data_length", "code_value",
        "code_meaning", "code_desc"]), DICTIONARY)

    assert result.unknown_words == ["XYZ"]


def test_trace_term_leaves_result_empty_when_a_word_is_unknown():
    trace = trace_term("trn_xyz_no", "CHAR", 5, 0, DICTIONARY)

    assert trace["cleaned"] == "TRN_XYZ_NO"
    assert trace["is_complete"] is False
    assert trace["term_kor"] == ""


def test_trace_term_builds_term_and_domain():
    trace = trace_term("TRN_NO", "CHAR", 5, 0, DICTIONARY)

    assert (trace["term_kor"], trace["domain"]) == ("열차번호", "번호C5")


def test_scoring_penalises_class_missing_from_word_dictionary(small_result):
    outputs = small_result.outputs

    scores = score_dictionaries(outputs["term_dict"], outputs["word_dict"], outputs["domain_dict"],
                                outputs["code_dict"])
    by_code = {item["code"]: item for item in scores["items"]}

    assert len(scores["items"]) == 31
    # 'ID' 는 한글이 없어 분류명이 '기타' 가 되는데, 단어사전에는 '기타' 라는 분류어가 없다
    assert by_code["INSPC_DOM_04"]["passed"] == by_code["INSPC_DOM_04"]["total"] - 1
    assert by_code["INSPC_TERM_03"]["score"] == 100.0
    assert by_code["INSPC_CODE_06"]["score"] == 100.0


def test_seed_sample_runs_end_to_end_without_unknown_words():
    columns = pd.DataFrame(json.loads((SEED / "columns.json").read_text(encoding="utf-8")))
    codes = pd.DataFrame(json.loads((SEED / "codes.json").read_text(encoding="utf-8")))
    words = json.loads((SEED / "words.json").read_text(encoding="utf-8"))

    result = run_pipeline(columns, codes, {word["abbr"]: word["name"] for word in words})

    assert result.unknown_words == []
    assert len(result.outputs["rejected"]) == 0
    assert len(result.outputs["column_definition"]) == len(columns)
