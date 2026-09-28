"""신호 태그와 증감률."""
import pandas as pd
import pytest

from pipeline import signals


@pytest.mark.parametrize("curr, prev, expected", [
    (120.0, 100.0, 20.0),
    (80.0, 100.0, -20.0),
    (100.0, 0.0, None),
    (100.0, None, None),
    (None, 100.0, None),
    (0.0, 100.0, None),
])
def test_it_yoy_pct(curr, prev, expected):
    out = signals.it_yoy_pct(pd.Series([curr], dtype="float64"), pd.Series([prev], dtype="float64")).iloc[0]
    assert (pd.isna(out) and expected is None) or out == pytest.approx(expected)


def _company(**over):
    row = {"it_yoy_pct": 25.0, "ciso_concurrent": True, "sec_staff_external": 1.5, "has_cert": False,
           "group_has_si": False, "emission_target": True, "factory_sido_count": 2}
    row.update(over)
    return pd.DataFrame([row]).astype({"ciso_concurrent": "boolean", "has_cert": "boolean",
                                       "group_has_si": "boolean", "emission_target": "boolean"})


def test_all_signals_in_fixed_order():
    assert signals.signal_tags(_company()).iloc[0] == signals.SIGNAL_ORDER


def test_signal_order_constant():
    assert signals.SIGNAL_ORDER == ["IT 투자 +20%", "CISO 겸직", "외부 보안인력", "인증 없음",
                                    "계열 SI 없음", "배출권 할당대상", "2개 이상 시도"]


def test_no_signals():
    tags = signals.signal_tags(_company(it_yoy_pct=19.9, ciso_concurrent=False, sec_staff_external=0.0,
                                        has_cert=True, group_has_si=True, emission_target=False,
                                        factory_sido_count=1)).iloc[0]
    assert tags == []


def test_yoy_threshold_is_inclusive():
    assert "IT 투자 +20%" in signals.signal_tags(_company(it_yoy_pct=20.0)).iloc[0]


def test_unknown_values_do_not_create_signals():
    tags = signals.signal_tags(_company(it_yoy_pct=None, ciso_concurrent=None, sec_staff_external=None,
                                        has_cert=None, emission_target=False, factory_sido_count=0)).iloc[0]
    assert tags == ["계열 SI 없음"]
