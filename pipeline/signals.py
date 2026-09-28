"""후보 목록의 신호 태그. 점수·순위가 아니라 해당 여부만 나열함 (SPEC 5장).

값을 모르는 경우(결측)에는 신호를 붙이지 않음.
"""
import pandas as pd

SIGNAL_ORDER = ["IT 투자 +20%", "CISO 겸직", "외부 보안인력", "인증 없음",
                "계열 SI 없음", "배출권 할당대상", "2개 이상 시도"]
YOY_THRESHOLD_PCT = 20.0  # 이 값 이상 증가하면 신호


def it_yoy_pct(curr: pd.Series, prev: pd.Series) -> pd.Series:
    """전년 대비 IT 투자 증감률(%). 두 해 모두 0보다 클 때만 계산함."""
    curr = pd.to_numeric(curr, errors="coerce").astype("float64")
    prev = pd.to_numeric(prev, errors="coerce").astype("float64")
    ok = (curr > 0) & (prev > 0)
    return ((curr / prev.where(ok) - 1) * 100).where(ok)


def _true(s: pd.Series) -> pd.Series:
    return s.astype("boolean").fillna(False).astype(bool)


def _false(s: pd.Series) -> pd.Series:
    return (~s.astype("boolean")).fillna(False).astype(bool)


def signal_tags(company: pd.Series | pd.DataFrame) -> pd.Series:
    number = lambda col: pd.to_numeric(company[col], errors="coerce")  # noqa: E731
    conditions = {
        # 120억/100억처럼 딱 20%인 경우 부동소수점으로 19.999…가 나오므로 반올림 후 비교함
        "IT 투자 +20%": (number("it_yoy_pct").round(6) >= YOY_THRESHOLD_PCT).fillna(False),
        "CISO 겸직": _true(company["ciso_concurrent"]),
        "외부 보안인력": (number("sec_staff_external") > 0).fillna(False),
        "인증 없음": _false(company["has_cert"]),
        "계열 SI 없음": ~_true(company["group_has_si"]),
        "배출권 할당대상": _true(company["emission_target"]),
        "2개 이상 시도": (number("factory_sido_count") >= 2).fillna(False),
    }
    flags = pd.DataFrame({name: conditions[name].to_numpy(dtype=bool) for name in SIGNAL_ORDER}, index=company.index)
    return pd.Series([[n for n in SIGNAL_ORDER if row[n]] for _, row in flags.iterrows()],
                     index=company.index, dtype=object)
