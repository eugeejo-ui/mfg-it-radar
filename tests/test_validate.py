"""쓰기 전 검증 게이트."""
import pandas as pd

from pipeline import validate

# 가짜 법인등록번호. 저장소 위생 검사가 13자리 숫자를 찾으므로 소스에는 나눠 적음
FAKE_JURIR = "110111" + "0000001"


def _company(n=3):
    return pd.DataFrame({"company_id": [f"회사{i}" for i in range(n)], "company_name": ["가"] * n})


def test_clean_table_passes():
    assert validate.table_problems("company", _company()) == []


def test_duplicate_key_is_reported():
    df = pd.concat([_company(), _company(1)], ignore_index=True)
    assert any("키 중복" in p for p in validate.table_problems("company", df))


def test_missing_required_column_is_reported():
    assert any("필수 열 없음" in p for p in validate.table_problems("company", _company().drop(columns="company_name")))


def test_row_drop_over_20_percent_is_reported():
    assert validate.row_drop_problems({"company": 79}, {"company": 100})
    assert validate.row_drop_problems({"company": 80}, {"company": 100}) == []
    assert validate.row_drop_problems({"company": 10}, {}) == []


def test_personal_column_name_is_reported():
    df = _company().assign(jurir_no="x")
    assert any("개인정보 열" in p for p in validate.privacy_problems(df))


def test_corporate_or_business_number_values_are_reported():
    for value in [FAKE_JURIR, "1234567890"]:
        df = _company().assign(note=pd.Series([value, None, "가"], dtype="string"))
        assert validate.privacy_problems(df), value


def test_other_codes_and_list_columns_pass():
    df = _company().assign(code=pd.Series(["E0036120001", "20111", "00126380"], dtype="string"),
                           tags=[["A"], [], [FAKE_JURIR + " 아님"]])
    assert validate.privacy_problems(df) == []
