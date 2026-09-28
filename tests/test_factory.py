"""산단공 전국 등록공장 정제."""
import pandas as pd
import pytest

from pipeline.sources import factory


@pytest.mark.parametrize("address, expected", [
    ("서울특별시 종로구 자하문로16길 8 (창성동)", "서울"),
    ("경기도 화성시 남양읍 1", "경기"),
    ("부산광역시 강서구 녹산산단", "부산"),
    ("세종특별자치시, 연서면 1", "세종"),
    ("강원특별자치도 원주시 1", "강원"),
    ("강원도 원주시 1", "강원"),
    ("충청북도 청주시 흥덕구 1", "충북"),
    ("충청남도 아산시 1", "충남"),
    ("전북특별자치도 완주군 1", "전북"),
    ("전라북도 군산시 1", "전북"),
    ("전라남도 여수시 1", "전남"),
    ("경상북도 구미시 1", "경북"),
    ("경상남도 창원시 성산구 1", "경남"),
    ("제주특별자치도 제주시 1", "제주"),
    ("제주특별자치 제주시 1", "제주"),
    ("제주도 서귀포시 1", "제주"),
    ("광주광역시 광산구 1", "광주"),
    ("울산광역시 남구 1", "울산"),
])
def test_sido_from_address(address, expected):
    assert factory.sido_from_address(pd.Series([address])).iloc[0] == expected


@pytest.mark.parametrize("address", ["경기동로 12", "동부로 3", "   ", "", None, "1219번지"])
def test_sido_unrecognized_is_missing(address):
    assert factory.sido_from_address(pd.Series([address])).isna().all()


@pytest.mark.parametrize("address, expected", [
    ("서울특별시 종로구 자하문로 8", "종로구"),
    ("경기도 화성시 남양읍 1", "화성시"),
    ("전북특별자치도 완주군 봉동읍 1", "완주군"),
    ("세종특별자치시 연서면 1", None),
    ("동부로 3 화성시", None),
])
def test_sigungu_from_address(address, expected):
    out = factory.sigungu_from_address(pd.Series([address])).iloc[0]
    assert (pd.isna(out) and expected is None) or out == expected


def _raw(rows):
    return pd.DataFrame(rows, columns=["순번", "회사명", "단지명", "생산품", "공장주소"])


def test_clean_factories_columns_and_flags():
    out = factory.clean_factories(_raw([
        [1, "(주)가상화학", " ", "합성수지", "울산광역시 남구 1"],
        [2, "가상화학 주식회사", "울산미포국가산업단지", "기초유기화학", "울산광역시 남구 2"],
    ]))
    assert out.columns.tolist() == ["seq", "company_name", "name_key", "complex_name", "in_complex",
                                    "products", "sido", "sigungu"]
    assert out["name_key"].tolist() == ["가상화학", "가상화학"]
    assert out["in_complex"].tolist() == [False, True]
    assert pd.isna(out.loc[0, "complex_name"])
    assert "공장주소" not in out.columns and "address" not in out.columns


def test_name_stats_counts_factories_provinces_and_products():
    f = factory.clean_factories(_raw([
        [1, "대원산업(주)", " ", "자동차부품", "경기도 화성시 1"],
        [2, "대원산업", " ", "자동차부품", "경기도 평택시 1"],
        [3, "대원산업", " ", "식품", "경상남도 김해시 1"],
        [4, "나기업", " ", "금속", "   "],
    ]))
    stats = factory.name_stats(f)
    assert stats.loc["대원산업"].tolist() == [3, 2, 2]
    assert stats.loc["나기업", "n_factories"] == 1
    assert stats.loc["나기업", "n_sido"] == 0
    assert stats.columns.tolist() == ["n_factories", "n_sido", "n_products"]


def test_raw_factory_regression(sources):
    f = sources.factories
    assert len(f) == 217048
    assert int(f["sido"].isna().sum()) == 1978
    assert f["name_key"].nunique() == 151227
    assert int(f["in_complex"].sum()) == 84111
    assert set(f["sido"].dropna()) == set(factory.SIDO_FORMS)
