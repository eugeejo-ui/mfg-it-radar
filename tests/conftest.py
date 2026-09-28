"""테스트 세션 공용 fixture.

원본 회귀 테스트는 원본을 한 번만 읽고(sources), 연간 빌드도 한 번만 돌림(built).
원본이 없는 환경(CI·Actions)에서는 이 fixture를 쓰는 테스트가 모두 건너뛰어짐.
"""
from types import SimpleNamespace

import pytest

from pipeline import manifest as mf


def _raw_available() -> bool:
    try:
        return all(mf.verify(entry) for entry in mf.load_manifest().values())
    except (FileNotFoundError, KeyError):
        return False


RAW_AVAILABLE = _raw_available()
SKIP_REASON = "원본 파일이 없는 환경(CI·Actions)"


@pytest.fixture(scope="session")
def sources():
    if not RAW_AVAILABLE:
        pytest.skip(SKIP_REASON)
    from pipeline.sources import factory, ftc, kisa, ngms
    membership, jurir, groups = ftc.load_ftc()
    factories = factory.load_factories()
    return SimpleNamespace(disclosure=kisa.load_kisa_disclosure(), membership=membership, jurir=jurir,
                           groups=groups, emission=ngms.load_emission(), factories=factories,
                           factory_stats=factory.name_stats(factories))


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    if not RAW_AVAILABLE:
        pytest.skip(SKIP_REASON)
    from pipeline import build
    out, cache = tmp_path_factory.mktemp("processed"), tmp_path_factory.mktemp("cache")
    return SimpleNamespace(result=build.build(out_dir=out, cache_dir=cache), out=out, cache=cache)
