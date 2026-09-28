"""원본 목록 모듈. 임시 폴더에 가짜 manifest와 파일을 만들어 검사함."""
import csv
import hashlib

import pytest

from pipeline import manifest as mf

COLUMNS = ["source_id", "file_name", "provider", "portal_url", "reference_date",
           "encoding", "sha256", "bytes", "rows", "note"]


def _write_manifest(raw_dir, rows):
    with open(raw_dir / "manifest.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def _entry(source_id, file_name, content=b"", **kw):
    row = {c: "" for c in COLUMNS}
    row.update(source_id=source_id, file_name=file_name,
               sha256=hashlib.sha256(content).hexdigest(), bytes=str(len(content)), rows="1")
    row.update(kw)
    return row


@pytest.fixture
def raw_dir(tmp_path):
    (tmp_path / "한글 파일.csv").write_bytes(b"a,b\n1,2\n")
    _write_manifest(tmp_path, [_entry("demo", "한글 파일.csv", b"a,b\n1,2\n", encoding="cp949")])
    return tmp_path


def test_load_manifest_reads_entries_by_source_id(raw_dir):
    entries = mf.load_manifest(raw_dir)
    assert set(entries) == {"demo"}
    assert entries["demo"].encoding == "cp949"
    assert entries["demo"].bytes == 8


def test_source_path_resolves_file(raw_dir):
    assert mf.source_path("demo", raw_dir) == raw_dir / "한글 파일.csv"


def test_source_path_unknown_id_raises(raw_dir):
    with pytest.raises(KeyError):
        mf.source_path("nope", raw_dir)


def test_source_path_missing_file_raises(raw_dir):
    (raw_dir / "한글 파일.csv").unlink()
    with pytest.raises(FileNotFoundError):
        mf.source_path("demo", raw_dir)


def test_verify_detects_changed_file(raw_dir):
    entry = mf.load_manifest(raw_dir)["demo"]
    assert mf.verify(entry, raw_dir)
    (raw_dir / "한글 파일.csv").write_bytes(b"a,b\n1,3\n")
    assert not mf.verify(entry, raw_dir)


def test_refresh_rewrites_hash_and_size_but_keeps_other_columns(raw_dir):
    (raw_dir / "한글 파일.csv").write_bytes(b"a,b\n1,2\n3,4\n")
    mf.refresh(raw_dir)
    entry = mf.load_manifest(raw_dir)["demo"]
    assert entry.sha256 == hashlib.sha256(b"a,b\n1,2\n3,4\n").hexdigest()
    assert entry.bytes == 12
    assert entry.encoding == "cp949"
    assert mf.verify(entry, raw_dir)
