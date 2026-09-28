"""NGMS 배출권거래제 할당대상업체 현황 정제 (docs/data-sources.md 2.4).

- 엑셀 2행이 빈 행이고 첫 열이 비어 있음 → skiprows=[1]로 읽고 Unnamed 열을 버림
- KSIC가 숫자로 저장되어 앞자리 0이 빠진 값이 있음 → 5자리로 되살림
- 업체코드는 NGMS 내부 코드라 다른 원본과 결합에 쓰지 않음 (업체명으로 결합)
"""
import pandas as pd

from pipeline import manifest as mf
from pipeline import normalize as nz
from pipeline.sources.common import read_excel


def clean_emission(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.loc[:, ~raw.columns.astype(str).str.startswith("Unnamed")].drop(columns=["NO"])
    out = pd.DataFrame(index=df.index)
    out["company_code"] = df["업체코드"].astype("string").str.strip()
    out["company_name"] = df["업체명"].astype("string").str.strip()
    out["name_key"] = out["company_name"].map(nz.name_key).astype("string")
    out["ksic5"] = nz.ksic5_from_ngms(df["KSIC 코드"])
    out["ksic2"] = nz.ksic2_from_ksic5(out["ksic5"])
    return out.reset_index(drop=True)


def load_emission(raw_dir=mf.RAW_DIR) -> pd.DataFrame:
    return clean_emission(read_excel("ngms_emission", raw_dir, header=0, skiprows=[1]))
