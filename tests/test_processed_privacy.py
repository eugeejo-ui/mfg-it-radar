"""커밋되는 data/processed/ 결과물에 개인정보가 없는지 확인함. 원본 없이 돌아 CI에서도 검사함."""
from pathlib import Path

import pandas as pd
import pytest

from pipeline import validate

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
FILES = sorted(p for p in PROCESSED.glob("*") if p.suffix in {".parquet", ".csv"})


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_processed_file_has_no_personal_data(path):
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, dtype="string")
    assert validate.privacy_problems(df) == []
