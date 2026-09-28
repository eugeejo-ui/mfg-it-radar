"""KISA 정보보호 공시 이행 기업 리스트 정제 (docs/data-sources.md 2.1).

- 한 행 = 회사 × 공시연도. 금액은 원 단위, 여부 열은 참거짓
- 수치를 공시 원문(첨부)으로 돌린 행은 figures_in_attachment로 표시하고 투자액·인력 수치를 결측으로 바꿈
  (0으로 두면 벤치마크에 가짜 0이 섞임)
- 투자·인력 수치의 기준 연도(공시연도의 전년인지)는 확정하지 못해 공시연도만 저장함
"""
import re

import pandas as pd

from pipeline import manifest as mf
from pipeline import normalize as nz
from pipeline.sources.common import read_excel

COLUMN_MAP = {
    "공시연도(yyyy)": "disclosure_year",
    "기업명": "company_name",
    "업종": "industry",
    "자율/의무": "filing_type",
    "사전점검 수행여부": "precheck",
    "투자현황_정보기술부문 투자액(A)": "it_invest_krw",
    "투자현황_정보보호부문 투자액(B)": "sec_invest_krw",
    "투자현황_주요 투자항목": "invest_items_text",
    "투자현황_비율(B/A)": "sec_invest_ratio_pct",
    "투자현황_특기사항": "invest_note",
    "인력현황_총임직원": "employees",
    "인력현황_정보기술부문 인력(C)": "it_staff",
    "인력현황_정보보호부문 내부인력": "sec_staff_internal",
    "인력현황_정보보호부문 외부인력": "sec_staff_external",
    "인력현황_정보보호부문 인력(D)": "sec_staff_total",
    "인력현황_비율(D/C)": "sec_staff_ratio_pct",
    "인력현황_CISO_직책명": "ciso_title",
    "인력현황_CISO_임원여부": "ciso_exec",
    "인력현황_CISO_겸직여부": "ciso_concurrent",
    "인력현황_CISO_주요활동건수": "ciso_activities",
    "인력현황_CPO_직책명": "cpo_title",
    "인력현황_CPO_임원여부": "cpo_exec",
    "인력현황_CPO_겸직여부": "cpo_concurrent",
    "인력현황_CPO_주요활동건수": "cpo_activities",
    "인력현황_특기사항": "staff_note",
    "정보보호 관련 인증·점검·평가 등에 관한 사항": "certs_text",
    "정보보호 활동 현황": "activities_text",
    "정보보호 투자우수기업 여부": "invest_excellent",
    "수정공시 여부": "corrected",
}
DROPPED_COLUMNS = ["정보보호 공시 우수기업"]  # 모든 행이 X

TEXT_COLUMNS = ["company_name", "invest_items_text", "invest_note", "ciso_title", "cpo_title",
                "staff_note", "certs_text", "activities_text"]
BOOL_COLUMNS = ["precheck", "ciso_exec", "ciso_concurrent", "cpo_exec", "cpo_concurrent",
                "invest_excellent", "corrected"]
FIGURE_COLUMNS = ["it_invest_krw", "sec_invest_krw", "sec_invest_ratio_pct", "employees", "it_staff",
                  "sec_staff_internal", "sec_staff_external", "sec_staff_total", "sec_staff_ratio_pct"]
NUMBER_COLUMNS = FIGURE_COLUMNS + ["ciso_activities", "cpo_activities"]

_REFERENCE = r"첨부|참조|참고|추가\s*기재"
_FIGURES_REFERENCE = _REFERENCE + r"|글로벌"
_PLACEHOLDER = r"\s*(?:0|-|\.|없음|해당\s*(?:사항)?\s*없음)\s*"

# 인식하는 인증. 순서가 결과 목록의 순서임. 대문자로 바꾼 문자열에 적용함
CERT_PATTERNS = {
    "ISMS-P": r"ISMS\s*[-–]?\s*P(?![A-Z])|정보\s*보호\s*및\s*개인\s*정보\S*\s*관리\s*체계",
    "ISMS": r"ISMS(?!\s*[-–]?\s*P(?![A-Z]))|(?<!개인)정보\s*보호\s*관리\s*체계",
    "ISO 27001": r"ISO\s*/?\s*(?:IEC\s*)?27001",
    "ISO 27701": r"ISO\s*/?\s*(?:IEC\s*)?27701",
    "ISO 27017": r"ISO\s*/?\s*(?:IEC\s*)?27017",
    "ISO 27018": r"ISO\s*/?\s*(?:IEC\s*)?27018",
    "ISO 22301": r"ISO\s*/?\s*(?:IEC\s*)?22301",
    "PCI-DSS": r"PCI\s*-?\s*DSS",
    "CSAP": r"CSAP|클라우드\s*(?:컴퓨팅\s*)?서비스\s*보안\s*인증",
    "SOC 2": r"SOC\s*2",
}
_CERT_REGEX = {name: re.compile(p) for name, p in CERT_PATTERNS.items()}


def parse_certs(text) -> list[str]:
    """인증 칸의 자유 기재 문자열에서 알려진 인증 이름을 뽑음."""
    if text is None or (not isinstance(text, str) and pd.isna(text)):
        return []
    upper = str(text).upper()
    return [name for name, regex in _CERT_REGEX.items() if regex.search(upper)]


def clean_kisa(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.drop(columns=DROPPED_COLUMNS, errors="ignore").rename(columns=COLUMN_MAP)

    for col in TEXT_COLUMNS:
        text = df[col].astype("string").str.strip()
        df[col] = text.mask(text == "")
    for col in NUMBER_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    for col in BOOL_COLUMNS:
        df[col] = nz.ox_to_bool(df[col])

    df["disclosure_year"] = pd.to_numeric(df["disclosure_year"]).astype("int64")
    df["name_key"] = df["company_name"].map(nz.name_key).astype("string")
    df["industry"] = nz.industry_label(df["industry"])
    df["mandatory"] = (df.pop("filing_type").astype("string").str.strip() == "의무").astype("boolean")

    notes = pd.concat([df["invest_items_text"], df["invest_note"], df["staff_note"]], axis=1).fillna("")
    refers = notes.apply(lambda s: s.str.contains(_FIGURES_REFERENCE, regex=True)).any(axis=1)
    no_staff = df["employees"].fillna(0) == 0
    it_zero = df["it_invest_krw"] == 0
    df["figures_in_attachment"] = (df["it_invest_krw"].isna() | (it_zero & (no_staff | refers))).astype("boolean")
    df.loc[df["figures_in_attachment"].to_numpy(dtype=bool), FIGURE_COLUMNS] = float("nan")

    items = df["invest_items_text"]
    df["items_in_attachment"] = items.str.contains(_REFERENCE, regex=True).fillna(False).astype("boolean")
    df["invest_items_text"] = items.mask(items.str.fullmatch(_PLACEHOLDER).fillna(False).astype(bool))

    df["certs"] = df["certs_text"].map(parse_certs)
    df["has_cert"] = df["certs"].map(bool).astype("boolean")
    return df


def load_kisa_disclosure(raw_dir=mf.RAW_DIR) -> pd.DataFrame:
    """manifest의 kisa_* 원본을 모두 읽어 한 테이블로 합침 (공시연도가 늘면 manifest에 추가만 하면 됨)."""
    frames = []
    for source_id in sorted(s for s in mf.load_manifest(raw_dir) if s.startswith("kisa_")):
        frames.append(clean_kisa(read_excel(source_id, raw_dir)))
    df = pd.concat(frames, ignore_index=True)
    return df.sort_values(["disclosure_year", "name_key"], ignore_index=True)


def select_targets(disclosure: pd.DataFrame, year: int, industry: str) -> pd.DataFrame:
    """대상 회사: 해당 공시연도·업종 대분류의 회사. company_id는 이름키(M3에서 corp_code로 바꿈)."""
    same_industry = (disclosure["industry"] == industry).fillna(False).astype(bool)  # 업종 결측 행은 제외
    rows = disclosure[(disclosure["disclosure_year"] == year) & same_industry].copy()
    rows.insert(0, "company_id", rows["name_key"])
    return rows.sort_values("company_id", ignore_index=True)
