"""연간 빌드 명령 (원본을 새로 받은 뒤 관리자 PC에서 실행).

    python -m pipeline.jobs.annual           빌드하고 data/processed/에 씀
    python -m pipeline.jobs.annual --check   빌드와 검증만 하고 쓰지 않음
"""
import argparse
import sys
from pathlib import Path

from pipeline import build


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline.jobs.annual", description="원본 → data/processed/ 연간 빌드")
    parser.add_argument("--check", action="store_true", help="빌드와 검증만 하고 파일을 쓰지 않음")
    parser.add_argument("--out", type=Path, default=build.PROCESSED_DIR, help="결과 폴더")
    parser.add_argument("--cache", type=Path, default=build.CACHE_DIR, help="로컬 캐시 폴더 (gitignore)")
    args = parser.parse_args(argv)

    try:
        result = build.build(out_dir=args.out, cache_dir=args.cache, write=not args.check)
    except build.BuildError as err:
        print("검증 실패 — 파일을 쓰지 않았습니다.")
        for problem in err.problems:
            print(f"  - {problem}")
        return 1

    print("테이블별 행 수")
    for name, df in result.tables.items():
        print(f"  {name:18} {len(df):>7,}")
    print("검수 목록")
    counts = result.review.groupby("category").size()
    for category, n in counts.items():
        print(f"  {category:18} {n:>7,}")
    if counts.empty:
        print("  없음")
    print(f"소요 시간 {result.elapsed_s:.1f}초")
    if args.check:
        print("검증만 했습니다 (--check). 파일은 쓰지 않았습니다.")
    else:
        print(f"저장: {args.out} ({len(result.written)}개 파일)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
