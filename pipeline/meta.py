"""출처·기준일 테이블(source_meta). 화면의 모든 블록이 출처와 기준일을 여기서 가져감."""
import pandas as pd

from pipeline.manifest import SourceEntry

COLUMNS = ["source_id", "provider", "portal_url", "reference_date", "rows", "note", "built_at"]


def source_meta(entries: dict[str, SourceEntry], rows: dict[str, int], built_at: str) -> pd.DataFrame:
    """빌드에 쓴 원본만 담음. rows는 빌드 때 실제로 읽은 행 수, built_at은 앱 캐시 키로 씀."""
    records = [{"source_id": sid, "provider": entries[sid].provider, "portal_url": entries[sid].portal_url,
                "reference_date": entries[sid].reference_date, "rows": n, "note": entries[sid].note,
                "built_at": built_at} for sid, n in rows.items()]
    df = pd.DataFrame(records, columns=COLUMNS)
    return df.astype({c: "string" for c in COLUMNS if c != "rows"}).astype({"rows": "int64"})
