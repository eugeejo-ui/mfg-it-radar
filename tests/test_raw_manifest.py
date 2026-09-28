"""원본 파일 목록(manifest)과 실제 원본 파일이 일치하는지 확인함.

원본은 커밋하지 않으므로 CI·Actions에서는 파일 검사를 건너뛰고 manifest 형식만 검사함.
"""
import csv
import hashlib
from pathlib import Path

import pytest

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
MANIFEST = RAW / "manifest.csv"
REQUIRED_COLUMNS = [
    "source_id", "file_name", "provider", "portal_url", "reference_date",
    "encoding", "sha256", "bytes", "rows", "note",
]


def _load_manifest():
    with open(MANIFEST, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _raw_files_present():
    return any(p.name != "manifest.csv" for p in RAW.iterdir() if p.is_file())


def test_manifest_has_required_columns():
    with open(MANIFEST, encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    assert header == REQUIRED_COLUMNS


def test_manifest_source_ids_are_unique():
    ids = [row["source_id"] for row in _load_manifest()]
    assert len(ids) == len(set(ids))


@pytest.mark.skipif(not _raw_files_present(), reason="원본 파일이 없는 환경(CI·Actions)")
@pytest.mark.parametrize("entry", _load_manifest(), ids=lambda e: e["source_id"])
def test_raw_file_matches_manifest(entry):
    path = RAW / entry["file_name"]
    assert path.exists(), f"원본 없음: {entry['file_name']}"
    assert path.stat().st_size == int(entry["bytes"])
    assert _sha256(path) == entry["sha256"]
