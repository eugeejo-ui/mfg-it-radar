"""연간 빌드: 원본 → 정제 → 결합 → 회사 요약 → 검증 → data/processed/ 쓰기.

- 대상 회사 = 최신 공시연도의 제조업. company_id를 정하는 곳은 assign_company_id 한 곳뿐임 (M3에서 corp_code로 바꿈)
- 원본 행은 대응표(xwalk)에서 use가 참인 (원본, 이름키)로만 대상 회사에 붙음
- 검증 게이트에 하나라도 걸리면 아무 파일도 쓰지 않음
"""
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from pipeline import ksic, match, meta, signals, validate
from pipeline import manifest as mf
from pipeline import normalize as nz
from pipeline.sources import factory, ftc, kisa, ngms

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
CACHE_DIR = ROOT / "data" / "cache"
MANUAL_DIR = ROOT / "data" / "manual"
TARGET_INDUSTRY = "제조업"
TOP_PRODUCTS = 3

COMPANY_BASE_COLUMNS = ["company_id", "name_key", "company_name", "industry", "employees", "it_invest_krw",
                        "it_staff", "sec_invest_krw", "sec_invest_ratio_pct", "ciso_exec", "ciso_concurrent",
                        "sec_staff_external", "certs", "has_cert", "items_in_attachment"]


class BuildError(RuntimeError):
    def __init__(self, problems: list[str]):
        super().__init__("검증 실패:\n" + "\n".join(problems))
        self.problems = problems


@dataclass
class BuildResult:
    tables: dict[str, pd.DataFrame]
    review: pd.DataFrame
    elapsed_s: float = 0.0
    written: list[Path] = field(default_factory=list)


def assign_company_id(targets: pd.DataFrame) -> pd.Series:
    """대상 회사 식별자. M1에서는 KISA 이름키, M3에서 DART corp_code로 바꿈."""
    return targets["name_key"].astype("string")


def _links(xwalk: pd.DataFrame, source: str) -> dict:
    rows = xwalk[(xwalk["source"] == source) & xwalk["use"].fillna(False).astype(bool)]
    return dict(zip(rows["name_key"], rows["company_id"]))


def _linked(frame: pd.DataFrame, xwalk: pd.DataFrame, source: str) -> pd.DataFrame:
    """원본 행에 company_id를 붙이고 결합된 행만 돌려줌."""
    out = frame.assign(company_id=frame["name_key"].map(_links(xwalk, source)).astype("string"))
    return out[out["company_id"].notna()]


def _by_company(frame: pd.DataFrame, column: str) -> dict:
    # groupby().agg(list)는 pyarrow 문자열 열에서 결과가 다시 문자열로 바뀜 → 직접 모음
    return {cid: values.tolist() for cid, values in frame.groupby("company_id")[column]}


def _top_products(products: list) -> list[str]:
    counts = pd.Series(products, dtype="string").dropna().value_counts()
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [name for name, _ in ranked[:TOP_PRODUCTS]]


def assemble_company(targets: pd.DataFrame, *, xwalk: pd.DataFrame, prev_year: int, prev: pd.DataFrame,
                     membership: pd.DataFrame, si: pd.DataFrame, emission: pd.DataFrame,
                     factories: pd.DataFrame) -> pd.DataFrame:
    c = targets[COMPANY_BASE_COLUMNS].copy().reset_index(drop=True)
    ids = c["company_id"].tolist()

    prev_rows = _linked(prev, xwalk, f"kisa_{prev_year}").drop_duplicates("company_id")
    c["it_invest_prev_krw"] = c["company_id"].map(dict(zip(prev_rows["company_id"], prev_rows["it_invest_krw"])))
    c["it_invest_prev_krw"] = c["it_invest_prev_krw"].astype("float64")
    c["it_yoy_pct"] = signals.it_yoy_pct(c["it_invest_krw"], c["it_invest_prev_krw"])
    c["size_band"] = nz.size_band(c["employees"])
    c["it_staff_ratio_pct"] = (c["it_staff"] / c["employees"].where(c["employees"] > 0) * 100).astype("float64")
    c["uses_external_sec_staff"] = (c["sec_staff_external"] > 0).astype("boolean").mask(c["sec_staff_external"].isna())

    mem = _linked(membership, xwalk, "ftc_affiliates")
    groups = {cid: sorted(set(v)) for cid, v in _by_company(mem, "group_name").items()}
    si_by_group = {g: sorted(set(v.tolist())) for g, v in si.groupby("group_name")["company_name"]}
    c["group_names"] = pd.Series([groups.get(cid, []) for cid in ids], dtype=object)
    c["in_group"] = pd.array([bool(groups.get(cid)) for cid in ids], dtype="boolean")
    si_names = [sorted({s for g in groups.get(cid, []) for s in si_by_group.get(g, [])}) for cid in ids]
    c["si_companies"] = pd.Series(si_names, dtype=object)
    c["group_has_si"] = pd.array([bool(s) for s in si_names], dtype="boolean")
    listed = {cid: any(bool(x) for x in v if pd.notna(x)) for cid, v in _by_company(mem, "listed").items()}
    c["listed"] = pd.array([listed.get(cid, pd.NA) for cid in ids], dtype="boolean")  # 집단 밖 회사는 M3에서 DART로 채움

    ftc_ksic = {cid: next((k for k in v if pd.notna(k)), None) for cid, v in _by_company(mem, "ksic2").items()}
    em = _linked(emission, xwalk, "ngms_emission")
    em_ksic = dict(zip(em["company_id"], em["ksic2"]))
    c["emission_target"] = pd.array([cid in em_ksic for cid in ids], dtype="boolean")
    ksic2 = [ftc_ksic.get(cid) or em_ksic.get(cid) for cid in ids]
    c["ksic2"] = pd.Series(ksic2, dtype="string")
    c["ksic2_source"] = pd.Series(["공정위" if ftc_ksic.get(cid) else ("배출권" if em_ksic.get(cid) else None)
                                   for cid in ids], dtype="string")
    c["ksic2_label"] = pd.Series([ksic.label(k) for k in ksic2], dtype="string")

    fac = _linked(factories, xwalk, "kicox_factories")
    sido = _by_company(fac, "sido")
    complex_ = _by_company(fac, "in_complex")
    products = _by_company(fac, "products")
    homonym = set(xwalk.loc[(xwalk["source"] == "kicox_factories") & (xwalk["status"] == "검수 필요")
                            & xwalk["use"].fillna(False).astype(bool), "company_id"])
    c["factory_count"] = pd.Series([len(sido.get(cid, [])) for cid in ids], dtype="int64")
    c["factory_sido"] = pd.Series([sorted({s for s in sido.get(cid, []) if pd.notna(s)}) for cid in ids], dtype=object)
    c["factory_sido_count"] = c["factory_sido"].map(len).astype("int64")
    c["multi_sido"] = (c["factory_sido_count"] >= 2).astype("boolean")
    c["complex_factory_count"] = pd.Series([sum(bool(x) for x in complex_.get(cid, []) if pd.notna(x)) for cid in ids],
                                           dtype="int64")
    c["top_products"] = pd.Series([_top_products(products.get(cid, [])) for cid in ids], dtype=object)
    c["factory_homonym_suspect"] = pd.array([cid in homonym for cid in ids], dtype="boolean")

    c["signals"] = signals.signal_tags(c)
    return c


def _with_company_id(frame: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    return frame.assign(company_id=frame["name_key"].map(mapping).astype("string"))


def _previous_rows(out_dir: Path) -> dict[str, int]:
    return {p.stem: pq.read_metadata(p).num_rows for p in Path(out_dir).glob("*.parquet")}


def build(raw_dir=mf.RAW_DIR, manual_dir=MANUAL_DIR, out_dir=PROCESSED_DIR, cache_dir=CACHE_DIR,
          write: bool = True) -> BuildResult:
    started = time.perf_counter()
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    disclosure = kisa.load_kisa_disclosure(raw_dir)
    year = int(disclosure["disclosure_year"].max())
    prev_year = year - 1
    current, prev = disclosure[disclosure["disclosure_year"] == year], disclosure[disclosure["disclosure_year"] == prev_year]
    targets = kisa.select_targets(disclosure, year, TARGET_INDUSTRY)
    targets["company_id"] = assign_company_id(targets)

    membership, jurir, groups = ftc.load_ftc(raw_dir)
    emission = ngms.load_emission(raw_dir)
    factories = factory.load_factories(raw_dir)

    xwalk = match.build_xwalk(targets, prev_year=prev_year, prev=prev, membership=membership, jurir=jurir,
                              emission=emission, factories=factories, factory_stats=factory.name_stats(factories))
    overrides = match.read_manual_csv(Path(manual_dir) / "xwalk_overrides.csv", match.OVERRIDE_COLUMNS)
    xwalk, override_problems = match.apply_overrides(xwalk, overrides, targets)
    review = match.review_queue(targets, xwalk, current, override_problems, prev_year=prev_year)
    si = ftc.find_si(membership, match.read_manual_csv(Path(manual_dir) / "si_manual.csv", match.SI_MANUAL_COLUMNS))

    company = assemble_company(targets, xwalk=xwalk, prev_year=prev_year, prev=prev, membership=membership,
                               si=si, emission=emission, factories=factories)

    current_ids = dict(zip(targets["name_key"], targets["company_id"]))
    prev_ids = _links(xwalk, f"kisa_{prev_year}")
    disclosure_out = pd.concat([_with_company_id(current, current_ids), _with_company_id(prev, prev_ids)])
    other_years = disclosure[~disclosure["disclosure_year"].isin([year, prev_year])].assign(company_id=pd.NA)
    if len(other_years):
        disclosure_out = pd.concat([disclosure_out, other_years.astype({"company_id": "string"})])

    si_lists = {g: sorted(set(v.tolist())) for g, v in si.groupby("group_name")["company_name"]}
    business_group = groups.assign(
        si_companies=pd.Series([si_lists.get(g, []) for g in groups["group_name"]], dtype=object, index=groups.index),
        has_si=pd.array([bool(si_lists.get(g)) for g in groups["group_name"]], dtype="boolean"))

    homonym = set(company.loc[company["factory_homonym_suspect"].astype(bool), "company_id"])
    factory_out = _linked(factories, xwalk, "kicox_factories")
    factory_out = factory_out.assign(homonym_suspect=factory_out["company_id"].isin(homonym).astype("boolean"))

    rows = {"kisa_" + str(y): int((disclosure["disclosure_year"] == y).sum()) for y in sorted(disclosure["disclosure_year"].unique())}
    rows.update({"ftc_affiliates": len(membership), "ftc_groups": len(groups), "ngms_emission": len(emission),
                 "kicox_factories": len(factories)})

    tables = {
        "company": company.sort_values("company_id"),
        "kisa_disclosure": disclosure_out.sort_values(["disclosure_year", "name_key"]),
        "group_membership": _with_company_id(membership, _links(xwalk, "ftc_affiliates")).sort_values(["group_name", "company_name"]),
        "business_group": business_group.sort_values("rank"),
        "emission_target": _with_company_id(emission, _links(xwalk, "ngms_emission")).sort_values("company_code"),
        "factory": factory_out.sort_values("seq"),
        "xwalk": xwalk.sort_values(["source", "name_key"]),
        "source_meta": meta.source_meta(mf.load_manifest(raw_dir), rows, built_at),
    }
    tables = {name: df.reset_index(drop=True) for name, df in tables.items()}

    problems = validate.validate_all(tables, _previous_rows(out_dir))
    if problems:
        raise BuildError(problems)

    result = BuildResult(tables=tables, review=review)
    if write:
        out_dir, cache_dir = Path(out_dir), Path(cache_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        for name, df in tables.items():
            path = out_dir / f"{name}.parquet"
            df.to_parquet(path, index=False)
            result.written.append(path)
        review_path = out_dir / "review_queue.csv"
        review.to_csv(review_path, index=False, encoding="utf-8-sig")  # 엑셀에서 한글이 깨지지 않게 BOM을 붙임
        result.written.append(review_path)
        jurir.to_parquet(cache_dir / "ftc_jurir.parquet", index=False)  # 법인등록번호: gitignore된 캐시에만 씀
    result.elapsed_s = time.perf_counter() - started
    return result
