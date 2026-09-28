"""이름키 결합, 대응표(xwalk), 사람이 고치는 덮어쓰기, 검수 목록.

- 대응표 한 행 = (원본, 이름키). use가 참인 행만 빌드에서 결합에 씀
- M1은 이름키 완전 일치만 씀. 표기가 달라 못 붙인 결합은 data/manual/xwalk_overrides.csv로 보완함
"""
from pathlib import Path

import pandas as pd

from pipeline import normalize as nz

HOMONYM_MIN_FACTORIES = 20  # 이름 하나에 전국 공장이 이만큼 이상이면 동명 회사가 섞였다고 봄
NONE = "NONE"  # 덮어쓰기에서 결합하지 않음을 뜻하는 값

XWALK_COLUMNS = ["source", "name_key", "source_name", "company_id", "method", "status", "use", "note"]
REVIEW_COLUMNS = ["category", "company_id", "company_name", "source", "detail"]
OVERRIDE_COLUMNS = ["source", "source_name", "company_id", "reason"]
SI_MANUAL_COLUMNS = ["group_name", "company_name", "reason"]
REVIEW_ORDER = ["공장 동명 의심", "공정위 이름 충돌", "전년 공시와 이름 불일치", "업종 결측", "덮어쓰기 오류"]


def _typed_xwalk(rows: pd.DataFrame) -> pd.DataFrame:
    out = rows.reindex(columns=XWALK_COLUMNS)
    for col in XWALK_COLUMNS:
        out[col] = out[col].astype("boolean" if col == "use" else "string")
    return out


def _match(targets: pd.DataFrame, frame: pd.DataFrame, source: str) -> pd.DataFrame:
    """frame의 이름키를 대상 회사에 맞춤. 완전 일치가 먼저이고, 없으면 영문 표기 변환 키로 맞춤.

    원본 표기는 이름키별 첫 표기를 씀.
    """
    names = frame.dropna(subset=["name_key"]).groupby("name_key", sort=True)["company_name"].first()
    ids = dict(zip(targets["name_key"], targets["company_id"]))
    by_translit: dict = {}
    for key, cid in ids.items():
        tk = nz.translit_key(key)
        by_translit[tk] = None if tk in by_translit else cid  # 변환 키가 겹치는 대상은 변환 결합에서 뺌
    rows = []
    for key in names.index:
        if key in ids:
            rows.append((key, ids[key], "이름 일치"))
        elif by_translit.get(nz.translit_key(key)):
            rows.append((key, by_translit[nz.translit_key(key)], "영문 표기 변환"))
    return _typed_xwalk(pd.DataFrame({
        "source": source, "name_key": [r[0] for r in rows], "source_name": [names[r[0]] for r in rows],
        "company_id": [r[1] for r in rows], "method": [r[2] for r in rows], "status": "확정", "use": True,
    }))


def build_xwalk(targets: pd.DataFrame, *, prev_year: int, prev: pd.DataFrame, membership: pd.DataFrame,
                jurir: pd.DataFrame, emission: pd.DataFrame, factories: pd.DataFrame,
                factory_stats: pd.DataFrame) -> pd.DataFrame:
    ftc_rows = _match(targets, membership, "ftc_affiliates")
    n_corp = jurir.dropna(subset=["name_key"]).groupby("name_key")["jurir_no"].nunique()
    shared = ftc_rows["name_key"].map(n_corp).fillna(1).astype(int)
    conflict = (shared > 1).to_numpy()
    ftc_rows.loc[conflict, ["status", "use"]] = ["검수 필요", False]
    ftc_rows.loc[conflict, "note"] = [f"이름이 같은 서로 다른 법인 {n}곳" for n in shared[conflict]]

    fac_rows = _match(targets, factories, "kicox_factories")
    stats = factory_stats.reindex(fac_rows["name_key"].tolist())
    homonym = (stats["n_factories"].fillna(0) >= HOMONYM_MIN_FACTORIES).to_numpy()
    fac_rows.loc[homonym, "status"] = "검수 필요"  # 결합은 유지하고 화면에 동명 가능성을 표시함
    fac_rows.loc[homonym, "note"] = [
        f"전국 공장 {int(r.n_factories)}곳 · {int(r.n_sido)}개 시도 · 생산품 {int(r.n_products)}종 — 동명 회사가 섞였을 수 있음"
        for r in stats[homonym].itertuples()]

    parts = [_match(targets, prev, f"kisa_{prev_year}"), ftc_rows,
             _match(targets, emission, "ngms_emission"), fac_rows]
    parts = [p for p in parts if len(p)]
    if not parts:
        return _typed_xwalk(pd.DataFrame(columns=XWALK_COLUMNS))
    return pd.concat(parts, ignore_index=True)


def apply_overrides(xwalk: pd.DataFrame, overrides: pd.DataFrame,
                    targets: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """덮어쓰기를 자동 결합보다 우선 적용함. 대상에 없는 company_id는 적용하지 않고 문제 목록으로 돌려줌."""
    xw = xwalk.copy()
    valid_ids = set(targets["company_id"])
    problems, added = [], []
    for o in overrides.itertuples(index=False):
        key = nz.name_key(o.source_name)
        company_id = str(o.company_id).strip()
        mask = ((xw["source"] == o.source) & (xw["name_key"] == key)).fillna(False).to_numpy(dtype=bool)
        if company_id != NONE and company_id not in valid_ids:
            problems.append({"category": "덮어쓰기 오류", "company_id": company_id, "company_name": pd.NA,
                             "source": o.source, "detail": f"'{o.source_name}' → 대상에 없는 company_id"})
            continue
        excluded = company_id == NONE
        values = {"company_id": pd.NA if excluded else company_id, "method": "수동",
                  "status": "제외" if excluded else "확정", "use": not excluded, "note": o.reason}
        if mask.any():
            for col, value in values.items():
                xw.loc[mask, col] = value
        else:
            added.append({"source": o.source, "name_key": key, "source_name": o.source_name, **values})
    if added:
        xw = pd.concat([xw, _typed_xwalk(pd.DataFrame(added))], ignore_index=True)
    return _typed_xwalk(xw), pd.DataFrame(problems, columns=REVIEW_COLUMNS)


def review_queue(targets: pd.DataFrame, xwalk: pd.DataFrame, current: pd.DataFrame,
                 problems: pd.DataFrame, prev_year: int) -> pd.DataFrame:
    """사람이 확인할 목록: 동명 의심 공장, 공정위 이름 충돌, 전년 공시 불일치, 업종 결측, 덮어쓰기 오류."""
    names = targets.set_index("company_id")["company_name"]
    rows = []
    needs_review = xwalk[xwalk["status"] == "검수 필요"]
    for r in needs_review.itertuples(index=False):
        category = {"kicox_factories": "공장 동명 의심", "ftc_affiliates": "공정위 이름 충돌"}.get(r.source)
        if category:
            rows.append({"category": category, "company_id": r.company_id, "company_name": names.get(r.company_id),
                         "source": r.source, "detail": r.note})

    prev_source = f"kisa_{prev_year}"
    linked = set(xwalk.loc[(xwalk["source"] == prev_source) & xwalk["use"].fillna(False), "company_id"])
    for r in targets[~targets["company_id"].isin(linked)].itertuples(index=False):
        rows.append({"category": "전년 공시와 이름 불일치", "company_id": r.company_id, "company_name": r.company_name,
                     "source": prev_source,
                     "detail": f"{prev_year} 공시에서 같은 이름을 찾지 못함 (신규 공시 또는 회사명 변경)"})

    for r in current[current["industry"].isna()].itertuples(index=False):
        rows.append({"category": "업종 결측", "company_id": r.name_key, "company_name": r.company_name,
                     "source": f"kisa_{prev_year + 1}", "detail": "업종이 비어 대상 여부를 판정할 수 없음"})

    review = pd.DataFrame(rows, columns=REVIEW_COLUMNS)
    if len(problems):
        review = pd.concat([review, problems], ignore_index=True)
    order = {c: i for i, c in enumerate(REVIEW_ORDER)}
    review = review.sort_values(["category", "company_id"], key=lambda s: s.map(order) if s.name == "category" else s)
    return review.reset_index(drop=True).astype("string")


def read_manual_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    """사람이 편집하는 CSV. 파일이 없거나 머리글만 있어도 열이 있는 빈 표를 돌려줌 (엑셀 저장 BOM 허용)."""
    if not Path(path).exists():
        return pd.DataFrame(columns=columns, dtype="string")
    return pd.read_csv(path, dtype="string", encoding="utf-8-sig").reindex(columns=columns)
