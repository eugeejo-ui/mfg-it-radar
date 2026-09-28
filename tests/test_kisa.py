"""KISA 정보보호 공시 정제."""
import pandas as pd
import pytest

from pipeline.sources import kisa

RAW_COLUMNS = [
    "공시연도(yyyy)", "기업명", "업종", "자율/의무", "사전점검 수행여부",
    "투자현황_정보기술부문 투자액(A)", "투자현황_정보보호부문 투자액(B)", "투자현황_주요 투자항목",
    "투자현황_비율(B/A)", "투자현황_특기사항", "인력현황_총임직원", "인력현황_정보기술부문 인력(C)",
    "인력현황_정보보호부문 내부인력", "인력현황_정보보호부문 외부인력", "인력현황_정보보호부문 인력(D)",
    "인력현황_비율(D/C)", "인력현황_CISO_직책명", "인력현황_CISO_임원여부", "인력현황_CISO_겸직여부",
    "인력현황_CISO_주요활동건수", "인력현황_CPO_직책명", "인력현황_CPO_임원여부", "인력현황_CPO_겸직여부",
    "인력현황_CPO_주요활동건수", "인력현황_특기사항", "정보보호 관련 인증·점검·평가 등에 관한 사항",
    "정보보호 활동 현황", "정보보호 공시 우수기업", "정보보호 투자우수기업 여부", "수정공시 여부",
]


def _row(**over):
    row = {
        "공시연도(yyyy)": 2026, "기업명": "(주)가상화학", "업종": "제조업(10~34)", "자율/의무": "의무",
        "사전점검 수행여부": "X", "투자현황_정보기술부문 투자액(A)": 4_000_000_000.0,
        "투자현황_정보보호부문 투자액(B)": 400_000_000.0, "투자현황_주요 투자항목": "EDR 도입",
        "투자현황_비율(B/A)": 10.0, "투자현황_특기사항": None, "인력현황_총임직원": 1239.6,
        "인력현황_정보기술부문 인력(C)": 20.0, "인력현황_정보보호부문 내부인력": 1.0,
        "인력현황_정보보호부문 외부인력": 0.5, "인력현황_정보보호부문 인력(D)": 1.5, "인력현황_비율(D/C)": 7.5,
        "인력현황_CISO_직책명": "상무", "인력현황_CISO_임원여부": "O", "인력현황_CISO_겸직여부": "O",
        "인력현황_CISO_주요활동건수": 3, "인력현황_CPO_직책명": "상무", "인력현황_CPO_임원여부": "O",
        "인력현황_CPO_겸직여부": "O", "인력현황_CPO_주요활동건수": 2, "인력현황_특기사항": None,
        "정보보호 관련 인증·점검·평가 등에 관한 사항": "ISO/IEC 27001 인증", "정보보호 활동 현황": "교육",
        "정보보호 공시 우수기업": "X", "정보보호 투자우수기업 여부": "O", "수정공시 여부": "X",
    }
    row.update(over)
    return row


def _clean(*rows):
    return kisa.clean_kisa(pd.DataFrame(list(rows), columns=RAW_COLUMNS))


def test_clean_renames_and_converts_types():
    out = _clean(_row()).iloc[0]
    assert out["disclosure_year"] == 2026
    assert out["company_name"] == "(주)가상화학"
    assert out["name_key"] == "가상화학"
    assert out["industry"] == "제조업"
    assert out["mandatory"] == True  # noqa: E712
    assert out["it_invest_krw"] == 4_000_000_000.0
    assert out["ciso_exec"] == True and out["ciso_concurrent"] == True  # noqa: E712
    assert out["invest_excellent"] == True and out["corrected"] == False  # noqa: E712
    assert out["sec_staff_external"] == 0.5


def test_clean_drops_always_empty_column():
    assert "정보보호 공시 우수기업" not in _clean(_row()).columns


def test_voluntary_filer_is_not_mandatory():
    assert _clean(_row(**{"자율/의무": "자율"})).iloc[0]["mandatory"] == False  # noqa: E712


@pytest.mark.parametrize("over", [
    {"투자현황_정보기술부문 투자액(A)": None},
    {"투자현황_정보기술부문 투자액(A)": 0.0, "인력현황_총임직원": 0.0},
    {"투자현황_정보기술부문 투자액(A)": 0.0, "투자현황_특기사항": "첨부된 정보보호 공시내용을 참조하여 주시기 바랍니다."},
    {"투자현황_정보기술부문 투자액(A)": 0.0, "인력현황_특기사항": "글로벌 차원에서 운영하여 국내 인력을 별도로 산정하지 않음"},
])
def test_figures_in_attachment_blanks_fake_zeros(over):
    out = _clean(_row(**over)).iloc[0]
    assert out["figures_in_attachment"] == True  # noqa: E712
    for col in ["it_invest_krw", "sec_invest_krw", "it_staff", "sec_staff_total", "employees"]:
        assert pd.isna(out[col]), col


def test_genuine_zero_investment_stays_zero():
    out = _clean(_row(**{"투자현황_정보기술부문 투자액(A)": 0.0, "투자현황_정보보호부문 투자액(B)": 0.0,
                         "인력현황_총임직원": 5.0, "투자현황_특기사항": "현 단계 정보보호 투자가 없음",
                         "투자현황_주요 투자항목": "없음"})).iloc[0]
    assert out["figures_in_attachment"] == False  # noqa: E712
    assert out["it_invest_krw"] == 0.0
    assert out["employees"] == 5.0


def test_items_pointing_to_attachment_are_flagged_but_figures_kept():
    out = _clean(_row(**{"투자현황_주요 투자항목": "첨부된 정보보호 공시내용을 참조하여 주시기 바랍니다."})).iloc[0]
    assert out["items_in_attachment"] == True  # noqa: E712
    assert out["figures_in_attachment"] == False  # noqa: E712
    assert out["it_invest_krw"] == 4_000_000_000.0


@pytest.mark.parametrize("placeholder", ["0", "-", ".", "없음", "해당사항 없음", " 해당 사항 없음 "])
def test_placeholder_items_become_missing(placeholder):
    assert pd.isna(_clean(_row(**{"투자현황_주요 투자항목": placeholder})).iloc[0]["invest_items_text"])


@pytest.mark.parametrize("text, expected", [
    ("ISO/IEC 27001 인증", ["ISO 27001"]),
    ("ISMS-P(정보보호 및 개인정보보호 관리체계)", ["ISMS-P"]),
    ("○ ISMS(정보보호 관리체계)", ["ISMS"]),
    ("ISMS 인증, ISMS-P 인증", ["ISMS-P", "ISMS"]),
    ("ISMS-P인증 (유효기간 2027)", ["ISMS-P"]),
    ("• 정보보호 및 개인정보보호 관리체계 인증서", ["ISMS-P"]),
    ("정보보호관리체계 인증(유효기간 : ‘23.11.15.)", ["ISMS"]),
    ("ISO27001, ISO 27701, ISO/IEC 27017, ISO 27018", ["ISO 27001", "ISO 27701", "ISO 27017", "ISO 27018"]),
    ("PCI DSS, PCI-DSS 인증", ["PCI-DSS"]),
    ("클라우드 서비스 보안인증(CSAP)", ["CSAP"]),
    ("SOC 2 Type II", ["SOC 2"]),
    ("ISO 22301", ["ISO 22301"]),
    ("해당사항없음", []),
    ("개인정보보호 자율점검", []),
    (None, []),
])
def test_parse_certs(text, expected):
    assert kisa.parse_certs(text) == expected


def test_has_cert_follows_parsed_certs():
    out = _clean(_row(), _row(**{"기업명": "나", "정보보호 관련 인증·점검·평가 등에 관한 사항": "해당사항 없음"}))
    assert out["has_cert"].tolist() == [True, False]


def test_select_targets_picks_year_and_industry():
    df = _clean(_row(), _row(**{"기업명": "가상통신", "업종": "정보통신업(58~63)"}),
                _row(**{"기업명": "(주)가상화학", "공시연도(yyyy)": 2025}))
    targets = kisa.select_targets(df, year=2026, industry="제조업")
    assert targets["company_id"].tolist() == ["가상화학"]
    assert targets["disclosure_year"].tolist() == [2026]


# ---- 원본 회귀 (conftest의 sources: 원본이 없으면 건너뜀) ----

@pytest.fixture
def disclosure(sources):
    return sources.disclosure


def test_raw_row_counts(disclosure):
    assert disclosure.groupby("disclosure_year").size().to_dict() == {2025: 773, 2026: 826}


def test_raw_2026_name_keys_are_unique(disclosure):
    assert not disclosure.loc[disclosure["disclosure_year"] == 2026, "name_key"].duplicated().any()


def test_raw_targets_are_387_manufacturers(disclosure):
    assert len(kisa.select_targets(disclosure, year=2026, industry="제조업")) == 387


def test_raw_attachment_flags(disclosure):
    d26 = disclosure[disclosure["disclosure_year"] == 2026]
    mfg = (d26["industry"] == "제조업").fillna(False)
    assert int(d26["figures_in_attachment"].sum()) == 16
    assert int((d26["figures_in_attachment"] & mfg).sum()) == 0
    assert int(d26["items_in_attachment"].sum()) == 7


def test_raw_cert_counts(disclosure):
    d26 = disclosure[disclosure["disclosure_year"] == 2026]
    counts = pd.Series([c for certs in d26["certs"] for c in certs]).value_counts().to_dict()
    assert counts == {"ISO 27001": 238, "ISMS": 230, "ISMS-P": 111, "ISO 27701": 70, "ISO 27017": 36,
                      "PCI-DSS": 32, "ISO 27018": 26, "CSAP": 17, "SOC 2": 13, "ISO 22301": 7}
    assert int(d26["has_cert"].sum()) == 419
    assert int(d26.loc[(d26["industry"] == "제조업").fillna(False), "has_cert"].sum()) == 127
