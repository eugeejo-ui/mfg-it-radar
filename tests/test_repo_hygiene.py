"""공개 저장소 위생: git에 올라가는 파일에 원본·키·캐시·개인정보 형태 값이 없는지 확인함.

git에 등록된(추적·스테이징) 파일만 검사함. 새 파일은 git add 후에 검사 대상이 됨.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("git") is None or not (ROOT / ".git").exists(),
                                reason="git 저장소가 아님")

FORBIDDEN_PATH = re.compile(r"^(data/raw/(?!manifest\.csv$).+|\.env$|data/cache/.*|\.venv/.*)")
SECRET_LIKE = r"\b[A-Za-z0-9]{40}\b|(^|[^0-9])[0-9]{13}([^0-9]|$)"  # DART 키(40자리), 법인등록번호(13자리)


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def test_no_forbidden_files_are_tracked():
    files = _git("-c", "core.quotepath=false", "ls-files").stdout.splitlines()
    assert [f for f in files if FORBIDDEN_PATH.match(f)] == []


def test_no_key_or_corporate_number_like_strings_in_tracked_text():
    # -I: 바이너리(parquet) 제외. parquet 안의 값은 test_processed_privacy가 검사함
    result = _git("grep", "-I", "-n", "-E", SECRET_LIKE, "--", ".", ":!data/raw/manifest.csv")
    assert result.returncode == 1, result.stdout  # 1 = 일치 없음
