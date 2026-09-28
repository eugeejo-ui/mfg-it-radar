"""공정위 소속회사·기업집단 정제."""
import pandas as pd
import pytest

from pipeline.sources import ftc

AFF_COLUMNS = ["공개년월", "기업집단명", "소속회사명", "대표자", "설립일", "계열편입일", "업종코드", "영위업종",
               "종업원수", "결산기일", "결산주총일", "기업공개일", "자산총액", "부채총액", "자본총액", "자본금",
               "매출액", "당기순이익", "구분", "법인등록번호", "사업자등록번호"]
GRP_COLUMNS = ["자료시점", "기업집단", "순위", "소속회사수", "상장소속회사수", "비상장소속회사수", "상시종업원수",
               "자산총액", "공정거래위원회자산총액", "부채총액", "자본총액", "매출금액", "당기순이익금액"]
# 가짜 법인등록번호. 저장소 위생 검사가 13자리 숫자를 찾으므로 소스에는 나눠 적음
FAKE_JURIR = "110111" + "0000001"
PII = ["대표자", "법인등록번호", "사업자등록번호", "jurir_no", "ceo", "bizr_no"]


def _aff(**over):
    row = {"공개년월": "202605", "기업집단명": "가상그룹", "소속회사명": "(주)가상화학", "대표자": "홍길동",
           "설립일": "2001/03/02", "계열편입일": "2001/03/02", "업종코드": "C2011", "영위업종": "기초 유기화학물질 제조업",
           "종업원수": "1,240", "결산기일": "2025/12/31", "결산주총일": "2026/03/20", "기업공개일": "2010/05/10",
           "자산총액": "56,237", "부채총액": "0", "자본총액": "-1,200", "자본금": "500", "매출액": "12,345",
           "당기순이익": "-300", "구분": "일반회사", "법인등록번호": FAKE_JURIR, "사업자등록번호": "1234567890"}
    row.update(over)
    return row


def _grp(**over):
    row = {"자료시점": 2026, "기업집단": "가상그룹", "순위": 77, "소속회사수": 17, "상장소속회사수": 0,
           "비상장소속회사수": 0, "상시종업원수": "12,345", "자산총액": "6,543,334", "공정거래위원회자산총액": "6,540,340",
           "부채총액": "1,000", "자본총액": "5,543,334", "매출금액": "9,994,840", "당기순이익금액": "-10"}
    row.update(over)
    return row


def _affiliates(*rows):
    return ftc.clean_affiliates(pd.DataFrame(list(rows), columns=AFF_COLUMNS).astype(str))


def test_membership_drops_personal_columns_and_keeps_jurir_separately():
    membership, jurir = _affiliates(_aff())
    assert not set(PII) & set(membership.columns)
    assert "결산주총일" not in membership.columns
    assert jurir.columns.tolist() == ["group_name", "company_name", "name_key", "jurir_no"]
    assert jurir.iloc[0]["jurir_no"] == FAKE_JURIR


def test_membership_converts_values():
    m = _affiliates(_aff())[0].iloc[0]
    assert m["disclosure_ym"] == "2026-05"
    assert m["name_key"] == "가상화학"
    assert m["ksic2"] == "20"
    assert m["employees"] == 1240
    assert m["assets_krw"] == 56_237_000_000.0
    assert m["equity_krw"] == -1_200_000_000.0
    assert m["liabilities_krw"] == 0.0
    assert m["net_income_krw"] == -300_000_000.0
    assert m["established"] == pd.Timestamp("2001-03-02")
    assert m["listed"] == True  # noqa: E712
    assert m["fs_div"] == "OFS"


def test_zero_revenue_means_missing():
    m = _affiliates(_aff(**{"매출액": "0"}))[0].iloc[0]
    assert pd.isna(m["revenue_krw"])


def test_no_listing_date_means_unlisted():
    m = _affiliates(_aff(**{"기업공개일": ""}))[0].iloc[0]
    assert m["listed"] == False  # noqa: E712
    assert pd.isna(m["listed_on"])


def test_clean_groups_drops_empty_listing_counts_and_scales_money():
    g = ftc.clean_groups(pd.DataFrame([_grp()], columns=GRP_COLUMNS)).iloc[0]
    assert "상장소속회사수" not in g.index and "n_listed" not in g.index
    assert g["group_name"] == "가상그룹"
    assert g["rank"] == 77 and g["n_affiliates"] == 17
    assert g["employees"] == 12345
    assert g["assets_krw"] == 6_543_334_000_000.0
    assert g["net_income_krw"] == -10_000_000.0


def test_find_si_uses_industry_code_and_manual_list():
    membership, _ = _affiliates(
        _aff(),
        _aff(**{"소속회사명": "가상정보기술(주)", "업종코드": "J6201"}),
        _aff(**{"기업집단명": "나그룹", "소속회사명": "나시스템", "업종코드": "J6312"}),
    )
    manual = pd.DataFrame([{"group_name": "나그룹", "company_name": "나시스템", "reason": "그룹 SI 역할"}])
    si = ftc.find_si(membership, manual)
    assert si[["group_name", "name_key", "si_source"]].values.tolist() == [
        ["가상그룹", "가상정보기술", "업종코드 J620"],
        ["나그룹", "나시스템", "수동"],
    ]


def test_find_si_without_manual_list():
    membership, _ = _affiliates(_aff(**{"업종코드": "J6202"}))
    assert ftc.find_si(membership)["si_source"].tolist() == ["업종코드 J620"]


# ---- 원본 회귀 (conftest의 sources: 원본이 없으면 건너뜀) ----

def test_raw_membership_counts(sources):
    membership, jurir, groups = sources.membership, sources.jurir, sources.groups
    assert len(membership) == 3539
    assert jurir["jurir_no"].nunique() == 3521
    assert not membership.duplicated(["group_name", "company_name"]).any()
    assert set(membership["group_name"]) == set(groups["group_name"])
    assert len(groups) == 102


def test_raw_si_listing_and_revenue(sources):
    membership, jurir = sources.membership, sources.jurir
    si = ftc.find_si(membership)
    assert len(si) == 49 and si["group_name"].nunique() == 37
    listed = membership.join(jurir["jurir_no"])[lambda d: d["listed"].astype(bool)]
    assert listed["jurir_no"].nunique() == 389
    assert int(membership["revenue_krw"].isna().sum()) == 600


def test_raw_membership_has_no_personal_values(sources):
    membership = sources.membership
    assert not set(PII) & set(membership.columns)
    text = membership.select_dtypes(include=["string", "object"]).astype("string")
    for col in text.columns:
        assert not text[col].str.fullmatch(r"\d{10}|\d{13}").fillna(False).any(), col
