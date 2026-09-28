"""배출권거래제 할당대상업체 정제."""
import pandas as pd
import pytest

from pipeline.sources import ngms


def _raw(rows):
    return pd.DataFrame(rows, columns=["Unnamed: 0", "NO", "업체코드", "업체명", "KSIC 코드"])


def test_clean_drops_blank_and_sequence_columns():
    out = ngms.clean_emission(_raw([[None, 1, "E0036120001", "(주)가상화학", 20111]]))
    assert out.columns.tolist() == ["company_code", "company_name", "name_key", "ksic5", "ksic2"]


def test_clean_restores_ksic_leading_zero_and_builds_name_key():
    out = ngms.clean_emission(_raw([[None, 1, "IA001200001", "가상광업 주식회사", 5100]])).iloc[0]
    assert out["ksic5"] == "05100"
    assert out["ksic2"] == "05"
    assert out["name_key"] == "가상광업"
    assert out["company_code"] == "IA001200001"


def test_raw_emission_regression(sources):
    df = sources.emission
    assert len(df) == 772
    assert df["company_code"].is_unique
    assert not df["name_key"].duplicated().any()
    assert int(df["ksic5"].str.startswith("0").sum()) == 3
    assert int(df["ksic2"].astype(int).between(10, 34).sum()) == 451
