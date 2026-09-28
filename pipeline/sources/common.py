"""원본을 source_id로 읽는 공통 함수."""
import warnings

import pandas as pd

from pipeline import manifest as mf


def read_excel(source_id: str, raw_dir=mf.RAW_DIR, **kwargs) -> pd.DataFrame:
    # 공공기관 엑셀 다수가 기본 스타일 없이 저장되어 openpyxl이 경고를 냄. 데이터와 무관하므로 이 경고만 숨김
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Workbook contains no default style", category=UserWarning)
        return pd.read_excel(mf.source_path(source_id, raw_dir), **kwargs)


def read_csv(source_id: str, raw_dir=mf.RAW_DIR, **kwargs) -> pd.DataFrame:
    """manifest의 encoding 값으로 CSV를 읽음."""
    entry = mf.load_manifest(raw_dir)[source_id]
    return pd.read_csv(mf.source_path(source_id, raw_dir), encoding=entry.encoding or "utf-8", **kwargs)
