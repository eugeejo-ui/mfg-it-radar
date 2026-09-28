"""공정위 기업집단포털: 소속회사 개요·기업집단별 개요 정제 (docs/data-sources.md 2.2, 2.3).

- 소속회사 한 행 = 회사 × 소속 집단. 두 집단에 동시 소속된 회사는 행이 2개임 (다대다)
- 대표자·사업자등록번호는 버리고, 법인등록번호는 따로 떼어 로컬 캐시(M3 정확 결합용)로만 넘김
- 금액은 백만원 × 10⁶ = 원 단위, 개별 기준(fs_div = OFS). 매출 0은 값 없음으로 봄
"""
import pandas as pd

from pipeline import manifest as mf
from pipeline import normalize as nz
from pipeline.sources.common import read_excel

MILLION = 1_000_000
AFF_MONEY = {"자산총액": "assets_krw", "부채총액": "liabilities_krw", "자본총액": "equity_krw",
             "자본금": "capital_krw", "매출액": "revenue_krw", "당기순이익": "net_income_krw"}
GRP_MONEY = {"자산총액": "assets_krw", "공정거래위원회자산총액": "ftc_assets_krw", "부채총액": "liabilities_krw",
             "자본총액": "equity_krw", "매출금액": "revenue_krw", "당기순이익금액": "net_income_krw"}
SI_CODE_PREFIX = "J620"


def _text(s: pd.Series) -> pd.Series:
    text = s.astype("string").str.strip()
    return text.mask(text == "")


def clean_affiliates(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """소속회사 개요 → (개인정보 없는 membership, 법인등록번호 캐시). 두 결과는 같은 행 순서·인덱스임."""
    m = pd.DataFrame(index=raw.index)
    ym = _text(raw["공개년월"])
    m["disclosure_ym"] = ym.str.slice(0, 4) + "-" + ym.str.slice(4, 6)
    m["group_name"] = _text(raw["기업집단명"])
    m["company_name"] = _text(raw["소속회사명"])
    m["name_key"] = m["company_name"].map(nz.name_key).astype("string")
    m["category"] = _text(raw["구분"])
    m["industry_code"] = _text(raw["업종코드"])
    m["ksic2"] = nz.ksic2_from_ftc(m["industry_code"])
    m["industry_name"] = _text(raw["영위업종"])
    m["employees"] = nz.parse_money(raw["종업원수"])
    m["established"] = nz.parse_date(raw["설립일"])
    m["affiliated_on"] = nz.parse_date(raw["계열편입일"])
    m["fiscal_year_end"] = nz.parse_date(raw["결산기일"])
    m["listed_on"] = nz.parse_date(raw["기업공개일"])
    m["listed"] = m["listed_on"].notna().astype("boolean")
    for src, dst in AFF_MONEY.items():
        m[dst] = nz.parse_money(raw[src], unit=MILLION)
    m["revenue_krw"] = m["revenue_krw"].mask(m["revenue_krw"] == 0)
    m["fs_div"] = pd.Series("OFS", index=raw.index, dtype="string")

    jurir = m[["group_name", "company_name", "name_key"]].copy()
    jurir["jurir_no"] = _text(raw["법인등록번호"])
    return m, jurir


def clean_groups(raw: pd.DataFrame) -> pd.DataFrame:
    g = pd.DataFrame(index=raw.index)
    g["data_year"] = pd.to_numeric(raw["자료시점"]).astype("int64")
    g["group_name"] = _text(raw["기업집단"])
    g["rank"] = pd.to_numeric(raw["순위"]).astype("int64")
    g["n_affiliates"] = pd.to_numeric(raw["소속회사수"]).astype("int64")
    g["employees"] = nz.parse_money(raw["상시종업원수"])
    for src, dst in GRP_MONEY.items():
        g[dst] = nz.parse_money(raw[src], unit=MILLION)
    return g.sort_values("rank", ignore_index=True)


def find_si(membership: pd.DataFrame, manual: pd.DataFrame | None = None) -> pd.DataFrame:
    """계열 SI: 업종코드가 J620으로 시작하는 소속회사 + 수동 보완 목록(data/manual/si_manual.csv)."""
    is_si = membership["industry_code"].str.startswith(SI_CODE_PREFIX).fillna(False).astype(bool)
    auto = membership.loc[is_si, ["group_name", "company_name", "name_key"]].assign(si_source="업종코드 J620")
    frames = [auto]
    if manual is not None and len(manual):
        added = manual[["group_name", "company_name"]].astype("string").copy()
        added["name_key"] = added["company_name"].map(nz.name_key).astype("string")
        frames.append(added.assign(si_source="수동"))
    si = pd.concat(frames, ignore_index=True)
    si["si_source"] = si["si_source"].astype("string")
    si = si.drop_duplicates(["group_name", "name_key"], keep="first")
    return si.sort_values(["group_name", "name_key"], ignore_index=True)


def load_ftc(raw_dir=mf.RAW_DIR) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(membership, jurir, groups). jurir는 법인등록번호를 담으므로 data/cache/ 밖에 쓰지 않음."""
    membership, jurir = clean_affiliates(read_excel("ftc_affiliates", raw_dir, dtype=str))
    groups = clean_groups(read_excel("ftc_groups", raw_dir))
    return membership, jurir, groups
