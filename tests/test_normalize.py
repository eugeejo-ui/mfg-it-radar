"""공통 정제 함수. 원본 없이 도는 표 형식 테스트."""
import math

import pandas as pd
import pytest

from pipeline import normalize as nz


@pytest.mark.parametrize("raw, expected", [
    ("(주)케이씨씨", "케이씨씨"),
    ("주식회사 에스씨케이컴퍼니", "에스씨케이컴퍼니"),
    ("동양이엔피 주식회사", "동양이엔피"),
    ("비에이치아이주식회사", "비에이치아이"),
    ("대원산업 (주)", "대원산업"),
    ("㈜abc 테크", "ABC테크"),
    ("HDC현대EP", "HDC현대EP"),
    ("(유)한빛", "한빛"),
    ("한빛 유한회사", "한빛"),
    ("유한책임회사 한빛", "한빛"),
    ("  ", None),
    (None, None),
    (float("nan"), None),
])
def test_name_key(raw, expected):
    assert nz.name_key(raw) == expected


@pytest.mark.parametrize("key, expected", [
    ("CJ제일제당", "씨제이제일제당"),
    ("HDC현대EP", "에이치디씨현대이피"),
    ("SK에너지", "에스케이에너지"),
    ("TCC스틸", "티씨씨스틸"),
    ("가상화학", "가상화학"),
    (None, None),
])
def test_translit_key_spells_latin_letters_in_korean(key, expected):
    assert nz.translit_key(key) == expected


def test_parse_money_handles_commas_blanks_and_unit():
    s = pd.Series(["56,237", "0", "", "-", None, 1200])
    out = nz.parse_money(s, unit=1_000_000)
    assert out.tolist()[:2] == [56_237_000_000.0, 0.0]
    assert out.iloc[2:5].isna().all()
    assert out.iloc[5] == 1_200_000_000.0
    assert out.dtype == "float64"


def test_parse_date_reads_slash_format_and_rejects_others():
    out = nz.parse_date(pd.Series(["2016/01/21", "1989/11/14", "", None, "2016-01-21x"]))
    assert out.iloc[0] == pd.Timestamp("2016-01-21")
    assert out.iloc[1] == pd.Timestamp("1989-11-14")
    assert out.iloc[2:].isna().all()


def test_ox_to_bool():
    out = nz.ox_to_bool(pd.Series(["O", "X", " O ", None, "?"]))
    assert out.iloc[:3].tolist() == [True, False, True]
    assert out.iloc[3:].isna().all()
    assert str(out.dtype) == "boolean"


@pytest.mark.parametrize("raw, expected", [
    ("제조업(10~34)", "제조업"),
    ("정보통신업(58~63)", "정보통신업"),
    ("교육 서비스업(85)", "교육 서비스업"),
    ("금융 및 보험업(64~66)", "금융 및 보험업"),
])
def test_industry_label(raw, expected):
    assert nz.industry_label(pd.Series([raw])).iloc[0] == expected


def test_industry_label_keeps_missing():
    assert nz.industry_label(pd.Series([None])).isna().all()


@pytest.mark.parametrize("raw, expected", [("C2011", "20"), ("J6201", "62"), ("R9112", "91")])
def test_ksic2_from_ftc(raw, expected):
    assert nz.ksic2_from_ftc(pd.Series([raw])).iloc[0] == expected


def test_ksic2_from_ftc_invalid_is_missing():
    assert nz.ksic2_from_ftc(pd.Series(["2011", None, "CC011"])).isna().all()


@pytest.mark.parametrize("raw, expected", [(5100, "05100"), (36020, "36020"), ("7110", "07110")])
def test_ksic5_from_ngms_restores_leading_zero(raw, expected):
    assert nz.ksic5_from_ngms(pd.Series([raw])).iloc[0] == expected


def test_ksic2_from_ksic5():
    assert nz.ksic2_from_ksic5(pd.Series(["05100", "36020", None])).tolist()[:2] == ["05", "36"]


@pytest.mark.parametrize("employees, expected", [
    (8.1, "300명 이하"),
    (300, "300명 이하"),
    (300.4, "300명 이하"),
    (300.5, "300~1,000명"),
    (1000, "300~1,000명"),
    (1000.6, "1,000~3,000명"),
    (3000, "1,000~3,000명"),
    (3000.5, "3,000명 초과"),
    (3511.1, "3,000명 초과"),
])
def test_size_band_boundaries(employees, expected):
    assert nz.size_band(pd.Series([employees])).iloc[0] == expected


@pytest.mark.parametrize("employees", [None, 0, -5, math.nan])
def test_size_band_missing_or_nonpositive(employees):
    assert nz.size_band(pd.Series([employees])).isna().all()


def test_size_bands_are_ordered():
    assert nz.SIZE_BANDS == ["300명 이하", "300~1,000명", "1,000~3,000명", "3,000명 초과"]
