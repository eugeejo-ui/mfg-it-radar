"""쓰기 전 검증 게이트. 하나라도 걸리면 빌드는 파일을 쓰지 않음."""
import re

import pandas as pd

TABLE_KEYS = {
    "company": ["company_id"],
    "kisa_disclosure": ["disclosure_year", "name_key"],
    "group_membership": ["group_name", "company_name"],
    "business_group": ["group_name"],
    "emission_target": ["company_code"],
    "factory": ["seq"],
    "xwalk": ["source", "name_key"],
    "source_meta": ["source_id"],
}
EXTRA_REQUIRED = {"company": ["company_name"]}
FORBIDDEN_COLUMNS = {"대표자", "법인등록번호", "사업자등록번호", "jurir_no", "bizr_no", "ceo_nm"}
MAX_ROW_DROP = 0.2
_ID_NUMBER = re.compile(r"\d{10}|\d{13}")  # 사업자등록번호 10자리, 법인등록번호 13자리


def table_problems(name: str, df: pd.DataFrame) -> list[str]:
    keys = TABLE_KEYS.get(name, [])
    missing = [c for c in keys + EXTRA_REQUIRED.get(name, []) if c not in df.columns]
    if missing:
        return [f"{name}: 필수 열 없음 {missing}"]
    dup = int(df.duplicated(keys).sum()) if keys else 0
    return [f"{name}: 키 중복 {dup}행 {keys}"] if dup else []


def privacy_problems(df: pd.DataFrame) -> list[str]:
    problems = []
    bad_cols = sorted(FORBIDDEN_COLUMNS & set(map(str, df.columns)))
    if bad_cols:
        problems.append(f"개인정보 열: {bad_cols}")
    for col in df.columns:
        if df[col].dtype.kind not in "OSU" and not isinstance(df[col].dtype, pd.StringDtype):
            continue
        hits = df[col].map(lambda v: isinstance(v, str) and bool(_ID_NUMBER.fullmatch(v.strip())))
        if hits.any():
            problems.append(f"개인정보 형태 값: {col} {int(hits.sum())}건")
    return problems


def row_drop_problems(current: dict[str, int], previous: dict[str, int]) -> list[str]:
    return [f"{name}: 행 수 급감 {previous[name]} → {rows}"
            for name, rows in current.items()
            if previous.get(name, 0) > 0 and rows < previous[name] * (1 - MAX_ROW_DROP)]


def validate_all(tables: dict[str, pd.DataFrame], previous_rows: dict[str, int]) -> list[str]:
    problems = []
    for name, df in tables.items():
        problems += table_problems(name, df)
        problems += [f"{name}: {p}" for p in privacy_problems(df)]
    problems += row_drop_problems({n: len(df) for n, df in tables.items()}, previous_rows)
    return problems
