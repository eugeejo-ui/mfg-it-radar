"""산단공 전국 등록공장 정제 (docs/data-sources.md 3장).

- 한 행 = 공장. 회사명으로만 결합할 수 있어 동명 회사가 섞임 → 이름별 전국 통계로 동명 여부를 판단함 (match.py)
- 주소 원문은 저장하지 않고 시도·시군구만 뽑음
"""
import pandas as pd

from pipeline import manifest as mf
from pipeline import normalize as nz
from pipeline.sources.common import read_csv

# 짧은 시도 이름 → 주소 첫 단어로 허용하는 표기. 첫 단어를 통째로 비교함 ('경기동로' 같은 도로명 오인 방지)
SIDO_FORMS = {
    "서울": ["서울특별시"], "부산": ["부산광역시"], "대구": ["대구광역시"], "인천": ["인천광역시"],
    "광주": ["광주광역시"], "대전": ["대전광역시"], "울산": ["울산광역시"], "세종": ["세종특별자치시"],
    "경기": ["경기도"], "강원": ["강원특별자치도", "강원도"], "충북": ["충청북도"], "충남": ["충청남도"],
    "전북": ["전북특별자치도", "전라북도"], "전남": ["전라남도"], "경북": ["경상북도"], "경남": ["경상남도"],
    "제주": ["제주특별자치도", "제주특별자치", "제주도"],
}
_FORM_TO_SIDO = {form: short for short, forms in SIDO_FORMS.items() for form in forms}


def _tokens(address: pd.Series) -> pd.Series:
    return address.astype("string").str.strip().str.split()


def sido_from_address(address: pd.Series) -> pd.Series:
    first = _tokens(address).str[0].astype("string").str.rstrip(",")
    return first.map(_FORM_TO_SIDO).astype("string")


def sigungu_from_address(address: pd.Series) -> pd.Series:
    """시도를 인식한 주소의 둘째 단어가 시·군·구로 끝나면 그 값."""
    second = _tokens(address).str[1].astype("string")
    ok = sido_from_address(address).notna() & second.str.contains(r"[시군구]$", regex=True).fillna(False)
    return second.where(ok.astype(bool))


def clean_factories(raw: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=raw.index)
    out["seq"] = pd.to_numeric(raw["순번"]).astype("int64")
    out["company_name"] = raw["회사명"].astype("string").str.strip()
    out["name_key"] = out["company_name"].map(nz.name_key).astype("string")
    complex_name = raw["단지명"].astype("string").str.strip()
    out["complex_name"] = complex_name.mask(complex_name == "")
    out["in_complex"] = out["complex_name"].notna().astype("boolean")
    out["products"] = raw["생산품"].astype("string").str.strip()
    out["sido"] = sido_from_address(raw["공장주소"])
    out["sigungu"] = sigungu_from_address(raw["공장주소"])
    return out.reset_index(drop=True)


def name_stats(factories: pd.DataFrame) -> pd.DataFrame:
    """이름키별 전국 공장 수, 시도 수, 생산품 종류 수 (동명 회사 판단용)."""
    grouped = factories.groupby("name_key")
    return pd.DataFrame({
        "n_factories": grouped.size(),
        "n_sido": grouped["sido"].nunique(),
        "n_products": grouped["products"].nunique(),
    }).astype("int64")


def load_factories(raw_dir=mf.RAW_DIR) -> pd.DataFrame:
    return clean_factories(read_csv("kicox_factories", raw_dir))
