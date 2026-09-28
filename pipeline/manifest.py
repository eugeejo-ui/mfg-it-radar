"""원본 파일 목록(data/raw/manifest.csv): source_id로 원본을 찾고 무결성을 확인함.

명령:
    python -m pipeline.manifest check     원본이 목록과 같은지 확인
    python -m pipeline.manifest refresh   원본을 교체한 뒤 sha256·크기를 다시 씀
"""
import csv
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
MANIFEST_NAME = "manifest.csv"
COLUMNS = ["source_id", "file_name", "provider", "portal_url", "reference_date",
           "encoding", "sha256", "bytes", "rows", "note"]


@dataclass(frozen=True)
class SourceEntry:
    source_id: str
    file_name: str
    provider: str
    portal_url: str
    reference_date: str
    encoding: str
    sha256: str
    bytes: int | None
    rows: int | None  # 등록할 때 확인한 행 수. 실제 빌드 행 수는 source_meta에 기록함
    note: str


def _to_int(value):
    return int(value) if value not in (None, "") else None


def _read_rows(raw_dir: Path) -> list[dict]:
    with open(raw_dir / MANIFEST_NAME, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_manifest(raw_dir: Path = RAW_DIR) -> dict[str, SourceEntry]:
    entries = {}
    for row in _read_rows(raw_dir):
        values = {c: row.get(c, "") for c in COLUMNS}
        values["bytes"] = _to_int(values["bytes"])
        values["rows"] = _to_int(values["rows"])
        entries[row["source_id"]] = SourceEntry(**values)
    return entries


def source_path(source_id: str, raw_dir: Path = RAW_DIR) -> Path:
    """source_id의 원본 경로. 목록에 없으면 KeyError, 파일이 없으면 FileNotFoundError."""
    entry = load_manifest(raw_dir)[source_id]
    path = raw_dir / entry.file_name
    if not path.exists():
        raise FileNotFoundError(f"{source_id}: {path}")
    return path


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(entry: SourceEntry, raw_dir: Path = RAW_DIR) -> bool:
    path = raw_dir / entry.file_name
    return path.exists() and path.stat().st_size == entry.bytes and file_sha256(path) == entry.sha256


def refresh(raw_dir: Path = RAW_DIR) -> list[str]:
    """목록에 있는 파일의 sha256·크기를 다시 계산해 씀. 바뀐 source_id를 돌려줌."""
    rows = _read_rows(raw_dir)
    changed = []
    for row in rows:
        path = raw_dir / row["file_name"]
        if not path.exists():
            raise FileNotFoundError(f"{row['source_id']}: {path}")
        sha, size = file_sha256(path), str(path.stat().st_size)
        if (row["sha256"], row["bytes"]) != (sha, size):
            row["sha256"], row["bytes"] = sha, size
            changed.append(row["source_id"])
    with open(raw_dir / MANIFEST_NAME, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows({c: row.get(c, "") for c in COLUMNS} for row in rows)
    return changed


def main(argv: list[str]) -> int:
    command = argv[0] if argv else "check"
    if command == "refresh":
        changed = refresh()
        print(f"갱신한 원본: {', '.join(changed) if changed else '없음'}")
        return 0
    if command == "check":
        failed = [sid for sid, e in load_manifest().items() if not verify(e)]
        for sid in load_manifest():
            print(f"{'불일치' if sid in failed else '일치':4} {sid}")
        return 1 if failed else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
