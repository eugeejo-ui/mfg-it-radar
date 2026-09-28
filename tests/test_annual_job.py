"""연간 빌드 명령의 동작 (인자 전달, 출력, 종료 코드).

빌드 자체와 파일 쓰기는 test_build.py가 conftest의 built로 검사함. 여기서는 빌드 함수를 바꿔 끼워 명령만 검사함.
"""
import pandas as pd
import pytest

from pipeline import build
from pipeline.jobs import annual


@pytest.fixture
def fake_build(monkeypatch):
    calls = []

    def _fake(**kwargs):
        calls.append(kwargs)
        tables = {"company": pd.DataFrame({"company_id": ["가"] * 387})}
        review = pd.DataFrame({"category": ["공장 동명 의심"] * 4})
        return build.BuildResult(tables=tables, review=review, elapsed_s=1.0,
                                 written=[] if not kwargs.get("write") else ["a", "b"])

    monkeypatch.setattr(build, "build", _fake)
    return calls


def test_check_mode_does_not_write(fake_build, tmp_path, capsys):
    code = annual.main(["--check", "--out", str(tmp_path / "out"), "--cache", str(tmp_path / "cache")])
    out = capsys.readouterr().out
    assert code == 0
    assert fake_build[0]["write"] is False
    assert fake_build[0]["out_dir"] == tmp_path / "out"
    assert "company" in out and "387" in out
    assert "검수 목록" in out and "공장 동명 의심" in out
    assert "쓰지 않았습니다" in out


def test_write_mode_reports_saved_files(fake_build, tmp_path, capsys):
    assert annual.main(["--out", str(tmp_path / "out")]) == 0
    assert fake_build[0]["write"] is True
    assert "저장" in capsys.readouterr().out


def test_build_error_returns_nonzero(monkeypatch, capsys):
    def failing_build(**kwargs):
        raise build.BuildError(["company: 키 중복 1행 ['company_id']"])

    monkeypatch.setattr(build, "build", failing_build)
    assert annual.main(["--check"]) == 1
    assert "키 중복" in capsys.readouterr().out
