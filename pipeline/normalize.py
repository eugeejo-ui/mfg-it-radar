"""여러 원본에 공통으로 쓰는 정제 규칙.

텍스트 결과는 결측이 pd.NA인 "string" dtype으로 돌려줌 (pandas 버전에 따라 동작이 바뀌지 않게 함).
"""
import re

import numpy as np
import pandas as pd

_CORP_MARKS = re.compile(r"\(주\)|㈜|주식회사|\(유\)|유한회사|유한책임회사|\s")

SIZE_BANDS = ["300명 이하", "300~1,000명", "1,000~3,000명", "3,000명 초과"]
_SIZE_BINS = [0, 300, 1000, 3000, np.inf]


def name_key(name):
    """회사명 결합 키: SPEC 7장 정규식으로 법인 표기와 공백을 지우고 영문을 대문자로 바꿈."""
    if name is None or (not isinstance(name, str) and pd.isna(name)):
        return None
    key = _CORP_MARKS.sub("", str(name)).upper()
    return key or None


# 영문 글자의 한글 발음. 원본마다 CJ제일제당/씨제이제일제당처럼 표기가 달라 두 번째 결합 키로 씀
_LETTER_NAMES = dict(A="에이", B="비", C="씨", D="디", E="이", F="에프", G="지", H="에이치", I="아이", J="제이",
                     K="케이", L="엘", M="엠", N="엔", O="오", P="피", Q="큐", R="알", S="에스", T="티", U="유",
                     V="브이", W="더블유", X="엑스", Y="와이", Z="제트")
_LATIN = re.compile(r"[A-Z]")


def translit_key(key):
    """이름키의 영문 글자를 한글 발음으로 바꾼 키 (예: CJ제일제당 → 씨제이제일제당). 완전 일치가 없을 때만 씀."""
    if key is None or (not isinstance(key, str) and pd.isna(key)):
        return None
    return _LATIN.sub(lambda m: _LETTER_NAMES[m.group()], key)


def parse_money(s: pd.Series, unit: float = 1.0) -> pd.Series:
    """쉼표 문자열이나 숫자를 float로 바꾸고 단위를 곱함. 빈 값과 '-'는 결측, 0은 0으로 둠."""
    text = s.astype("string").str.replace(",", "", regex=False).str.strip()
    num = pd.to_numeric(text, errors="coerce")
    values = pd.Series(num).to_numpy(dtype="float64", na_value=np.nan)
    return pd.Series(values, index=s.index) * unit


def parse_date(s: pd.Series) -> pd.Series:
    """공정위 날짜 형식 YYYY/MM/DD를 날짜로 바꿈. 형식이 다르면 결측."""
    return pd.to_datetime(s.astype("string"), format="%Y/%m/%d", errors="coerce")


def ox_to_bool(s: pd.Series) -> pd.Series:
    """KISA 여부 열: O → True, X → False, 그 밖 → 결측."""
    text = s.astype("string").str.strip()
    return text.map({"O": True, "X": False}).astype("boolean")


def industry_label(s: pd.Series) -> pd.Series:
    """KISA 업종 표기 '제조업(10~34)'에서 괄호의 코드 범위를 뗌."""
    return s.astype("string").str.replace(r"\s*\([^)]*\)\s*$", "", regex=True).str.strip()


def ksic2_from_ftc(s: pd.Series) -> pd.Series:
    """공정위 업종코드 'C2011'(영문 대분류 + 4자리)에서 중분류 2자리를 뽑음."""
    return s.astype("string").str.extract(r"^[A-U](\d{2})\d{2}$", expand=False)


def ksic5_from_ngms(s: pd.Series) -> pd.Series:
    """배출권 KSIC: 숫자로 저장되어 빠진 앞자리 0을 되살려 5자리로 맞춤."""
    text = s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    valid = text.str.fullmatch(r"\d{4,5}").fillna(False).astype(bool)
    return text.where(valid).str.zfill(5)


def ksic2_from_ksic5(s: pd.Series) -> pd.Series:
    """KSIC 5자리에서 중분류 2자리를 뽑음."""
    text = s.astype("string")
    valid = text.str.fullmatch(r"\d{5}").fillna(False).astype(bool)
    return text.where(valid).str.slice(0, 2)


def size_band(employees: pd.Series) -> pd.Series:
    """임직원 수 → 규모 구간. 반올림(0.5는 올림) 후 경계값은 아래 구간에 넣음."""
    x = pd.to_numeric(employees, errors="coerce").astype("float64")
    rounded = np.floor(x + 0.5)
    return pd.cut(rounded, bins=_SIZE_BINS, labels=SIZE_BANDS, right=True)
