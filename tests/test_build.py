"""회사 요약 조립 규칙과 원본 전체 빌드."""
import pandas as pd
import pytest

from pipeline import build, match


def _targets():
    return pd.DataFrame({
        "company_id": ["가상화학", "나전자"], "name_key": ["가상화학", "나전자"],
        "company_name": ["(주)가상화학", "나전자"], "industry": ["제조업", "제조업"],
        "employees": [1239.6, 250.0], "it_invest_krw": [12e9, 3e9], "it_staff": [30.0, 5.0],
        "sec_invest_krw": [1e9, 0.3e9], "sec_invest_ratio_pct": [8.3, 10.0],
        "ciso_exec": [True, False], "ciso_concurrent": [True, True], "sec_staff_external": [2.0, 0.0],
        "certs": [["ISMS"], []], "has_cert": [True, False], "items_in_attachment": [False, False],
    }).astype({"ciso_exec": "boolean", "ciso_concurrent": "boolean", "has_cert": "boolean",
               "items_in_attachment": "boolean"})


def _xwalk(rows):
    df = pd.DataFrame(rows, columns=["source", "name_key", "company_id", "status", "use"])
    df["source_name"] = df["name_key"]
    df["method"] = "이름 일치"
    df["note"] = pd.NA
    return df[match.XWALK_COLUMNS]


def _assemble(xwalk_rows, **over):
    inputs = {
        "prev": pd.DataFrame({"name_key": ["가상화학"], "it_invest_krw": [10e9]}),
        "membership": pd.DataFrame({"group_name": ["가상그룹", "가상그룹"], "name_key": ["가상화학", "가상정보기술"],
                                    "ksic2": ["20", "62"], "listed": [True, False]}),
        "si": pd.DataFrame({"group_name": ["가상그룹"], "company_name": ["가상정보기술(주)"]}),
        "emission": pd.DataFrame({"name_key": ["가상화학", "나전자"], "ksic2": ["24", "26"]}),
        "factories": pd.DataFrame({
            "name_key": ["가상화학"] * 4 + ["나전자"],
            "sido": ["울산", "울산", "경기", None, "경북"],
            "in_complex": [True, True, False, False, True],
            "products": ["합성수지", "합성수지", "기초화학", "도료", "반도체"],
        }),
    }
    inputs.update(over)
    return build.assemble_company(_targets(), xwalk=_xwalk(xwalk_rows), prev_year=2025, **inputs).set_index("company_id")


ALL_LINKS = [
    ["kisa_2025", "가상화학", "가상화학", "확정", True],
    ["ftc_affiliates", "가상화학", "가상화학", "확정", True],
    ["ngms_emission", "가상화학", "가상화학", "확정", True],
    ["ngms_emission", "나전자", "나전자", "확정", True],
    ["kicox_factories", "가상화학", "가상화학", "확정", True],
    ["kicox_factories", "나전자", "나전자", "검수 필요", True],
]


def test_ksic2_prefers_ftc_then_emission():
    c = _assemble(ALL_LINKS)
    assert (c.loc["가상화학", "ksic2"], c.loc["가상화학", "ksic2_source"]) == ("20", "공정위")
    assert (c.loc["나전자", "ksic2"], c.loc["나전자", "ksic2_source"]) == ("26", "배출권")
    assert c.loc["가상화학", "ksic2_label"] == "화학"


def test_group_and_si():
    c = _assemble(ALL_LINKS)
    assert list(c.loc["가상화학", "group_names"]) == ["가상그룹"]
    assert c.loc["가상화학", "group_has_si"] == True  # noqa: E712
    assert list(c.loc["가상화학", "si_companies"]) == ["가상정보기술(주)"]
    assert c.loc["가상화학", "listed"] == True  # noqa: E712
    assert list(c.loc["나전자", "group_names"]) == []
    assert c.loc["나전자", "group_has_si"] == False  # noqa: E712
    assert pd.isna(c.loc["나전자", "listed"])


def test_factory_aggregates():
    c = _assemble(ALL_LINKS)
    a = c.loc["가상화학"]
    assert a["factory_count"] == 4
    assert list(a["factory_sido"]) == ["경기", "울산"]
    assert a["factory_sido_count"] == 2
    assert a["complex_factory_count"] == 2
    assert list(a["top_products"]) == ["합성수지", "기초화학", "도료"]
    assert a["factory_homonym_suspect"] == False  # noqa: E712
    assert c.loc["나전자", "factory_homonym_suspect"] == True  # noqa: E712


def test_unused_links_are_ignored():
    links = [r if r[0] != "ngms_emission" else [*r[:3], "제외", False] for r in ALL_LINKS]
    c = _assemble(links)
    assert c["emission_target"].tolist() == [False, False]


def test_yoy_size_band_ratios_and_signals():
    c = _assemble(ALL_LINKS)
    a = c.loc["가상화학"]
    assert a["it_invest_prev_krw"] == 10e9
    assert a["it_yoy_pct"] == pytest.approx(20.0)
    assert a["size_band"] == "1,000~3,000명"
    assert a["it_staff_ratio_pct"] == pytest.approx(30 / 1239.6 * 100)
    assert a["uses_external_sec_staff"] == True  # noqa: E712
    assert list(a["signals"]) == ["IT 투자 +20%", "CISO 겸직", "외부 보안인력", "배출권 할당대상", "2개 이상 시도"]
    assert pd.isna(c.loc["나전자", "it_yoy_pct"])


def test_assign_company_id_is_name_key_until_dart():
    t = _targets()
    assert build.assign_company_id(t).tolist() == ["가상화학", "나전자"]


# ---- 원본 전체 빌드 (conftest의 built: 원본이 없으면 건너뜀) ----

def test_raw_build_tables_and_rows(built):
    rows = {name: len(df) for name, df in built.result.tables.items()}
    assert rows == {"company": 387, "kisa_disclosure": 1599, "group_membership": 3539, "business_group": 102,
                    "emission_target": 772, "factory": 1389, "xwalk": 980, "source_meta": 6}
    assert sorted(p.name for p in built.out.iterdir()) == sorted([f"{n}.parquet" for n in rows] + ["review_queue.csv"])
    assert (built.cache / "ftc_jurir.parquet").exists()


def test_raw_build_company_regression(built):
    c = built.result.tables["company"]
    tags = pd.Series([t for ts in c["signals"] for t in ts]).value_counts().to_dict()
    assert tags == {"IT 투자 +20%": 102, "CISO 겸직": 318, "외부 보안인력": 200, "인증 없음": 260,
                    "계열 SI 없음": 315, "배출권 할당대상": 145, "2개 이상 시도": 214}
    assert int(c["it_yoy_pct"].notna().sum()) == 351
    assert int(c["ksic2"].notna().sum()) == 191
    assert int(c["in_group"].sum()) == 131
    assert int(c["listed"].fillna(False).sum()) == 123
    assert int(c["factory_count"].gt(0).sum()) == 340
    assert int(c["complex_factory_count"].sum()) == 851
    assert int(c["factory_homonym_suspect"].sum()) == 4


def test_raw_build_links_and_privacy(built):
    t = built.result.tables
    assert int(t["kisa_disclosure"]["company_id"].notna().sum()) == 387 + 351
    assert int(t["group_membership"]["company_id"].notna().sum()) == 132  # 두 집단 소속 1곳 포함
    assert int(t["emission_target"]["company_id"].notna().sum()) == 145
    assert int(t["business_group"]["has_si"].sum()) == 38  # J620 37개 + 수동 보완(포스코)
    assert built.result.review.groupby("category").size().to_dict() == {
        "공장 동명 의심": 4, "전년 공시와 이름 불일치": 36, "업종 결측": 6}
    from pipeline import validate
    for name, df in t.items():
        assert validate.privacy_problems(df) == [], name
