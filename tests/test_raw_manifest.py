"""원본 파일 목록(manifest)과 실제 원본 파일이 일치하는지 확인함.

원본은 커밋하지 않으므로 CI·Actions에서는 파일 검사를 건너뛰고 manifest 형식만 검사함.
"""
import csv

import pytest

from pipeline import manifest as mf


def _raw_files_present():
    return any(p.name != mf.MANIFEST_NAME for p in mf.RAW_DIR.iterdir() if p.is_file())


def test_manifest_has_required_columns():
    with open(mf.RAW_DIR / mf.MANIFEST_NAME, encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    assert header == mf.COLUMNS


def test_manifest_source_ids_are_unique():
    with open(mf.RAW_DIR / mf.MANIFEST_NAME, encoding="utf-8", newline="") as f:
        ids = [row["source_id"] for row in csv.DictReader(f)]
    assert len(ids) == len(set(ids))


@pytest.mark.skipif(not _raw_files_present(), reason="원본 파일이 없는 환경(CI·Actions)")
@pytest.mark.parametrize("entry", mf.load_manifest().values(), ids=lambda e: e.source_id)
def test_raw_file_matches_manifest(entry):
    assert (mf.RAW_DIR / entry.file_name).exists(), f"원본 없음: {entry.file_name}"
    assert mf.verify(entry)
