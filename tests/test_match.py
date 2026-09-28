"""이름 결합, 대응표, 덮어쓰기, 검수 목록."""
import pandas as pd
import pytest

from pipeline import match


def _targets(*names):
    return pd.DataFrame({"company_id": list(names), "name_key": list(names),
                         "company_name": [f"(주){n}" for n in names]})


def _frame(rows, columns):
    return pd.DataFrame(rows, columns=columns)


EMPTY = {
    "prev": _frame([], ["name_key", "company_name", "disclosure_year"]),
    "membership": _frame([], ["group_name", "company_name", "name_key"]),
    "jurir": _frame([], ["group_name", "company_name", "name_key", "jurir_no"]),
    "emission": _frame([], ["company_name", "name_key"]),
    "factories": _frame([], ["company_name", "name_key"]),
    "factory_stats": pd.DataFrame(columns=["n_factories", "n_sido", "n_products"]).rename_axis("name_key"),
}


def _xwalk(targets, **over):
    kwargs = {**EMPTY, **over}
    return match.build_xwalk(targets, prev_year=2025, **kwargs)


def _row(xw, source, name_key):
    rows = xw[(xw["source"] == source) & (xw["name_key"] == name_key)]
    assert len(rows) == 1, rows
    return rows.iloc[0]


def test_exact_name_match_is_confirmed():
    xw = _xwalk(_targets("가상화학"), emission=_frame([["가상화학 주식회사", "가상화학"]], ["company_name", "name_key"]))
    r = _row(xw, "ngms_emission", "가상화학")
    assert (r["company_id"], r["method"], r["status"], bool(r["use"])) == ("가상화학", "이름 일치", "확정", True)
    assert r["source_name"] == "가상화학 주식회사"
    assert xw.columns.tolist() == match.XWALK_COLUMNS


def test_latin_target_matches_korean_spelling_in_source():
    membership = _frame([["CJ그룹", "씨제이제일제당(주)", "씨제이제일제당"]], ["group_name", "company_name", "name_key"])
    jurir = _frame([["CJ그룹", "씨제이제일제당(주)", "씨제이제일제당", "1"]], ["group_name", "company_name", "name_key", "jurir_no"])
    r = _row(_xwalk(_targets("CJ제일제당"), membership=membership, jurir=jurir), "ftc_affiliates", "씨제이제일제당")
    assert (r["company_id"], r["method"], r["status"], bool(r["use"])) == ("CJ제일제당", "영문 표기 변환", "확정", True)


def test_korean_target_matches_latin_spelling_in_source():
    xw = _xwalk(_targets("티씨씨스틸"), emission=_frame([["TCC스틸", "TCC스틸"]], ["company_name", "name_key"]))
    r = _row(xw, "ngms_emission", "TCC스틸")
    assert (r["company_id"], r["method"]) == ("티씨씨스틸", "영문 표기 변환")


def test_exact_match_wins_over_transliteration():
    xw = _xwalk(_targets("LG화학", "엘지화학"),
                emission=_frame([["엘지화학", "엘지화학"]], ["company_name", "name_key"]))
    r = _row(xw, "ngms_emission", "엘지화학")
    assert (r["company_id"], r["method"]) == ("엘지화학", "이름 일치")


def test_unmatched_names_create_no_rows():
    xw = _xwalk(_targets("가상화학"), emission=_frame([["다른회사", "다른회사"]], ["company_name", "name_key"]))
    assert xw.empty


def test_prev_disclosure_source_is_named_by_year():
    xw = _xwalk(_targets("가상화학"), prev=_frame([["가상화학", "가상화학㈜", 2025]], ["name_key", "company_name", "disclosure_year"]))
    assert _row(xw, "kisa_2025", "가상화학")["status"] == "확정"


def test_ftc_name_shared_by_two_corporations_needs_review_and_is_not_used():
    membership = _frame([["A그룹", "(주)동림", "동림"], ["B그룹", "(주)동림", "동림"]], ["group_name", "company_name", "name_key"])
    jurir = _frame([["A그룹", "(주)동림", "동림", "1"], ["B그룹", "(주)동림", "동림", "2"]],
                   ["group_name", "company_name", "name_key", "jurir_no"])
    r = _row(_xwalk(_targets("동림"), membership=membership, jurir=jurir), "ftc_affiliates", "동림")
    assert (r["status"], bool(r["use"])) == ("검수 필요", False)
    assert "2곳" in r["note"]


def test_ftc_same_corporation_in_two_groups_is_one_confirmed_row():
    membership = _frame([["A그룹", "(주)씨텍", "씨텍"], ["B그룹", "(주)씨텍", "씨텍"]], ["group_name", "company_name", "name_key"])
    jurir = _frame([["A그룹", "(주)씨텍", "씨텍", "1"], ["B그룹", "(주)씨텍", "씨텍", "1"]],
                   ["group_name", "company_name", "name_key", "jurir_no"])
    r = _row(_xwalk(_targets("씨텍"), membership=membership, jurir=jurir), "ftc_affiliates", "씨텍")
    assert (r["status"], bool(r["use"])) == ("확정", True)


def test_factory_homonym_needs_review_but_is_still_used():
    stats = pd.DataFrame({"n_factories": [25], "n_sido": [9], "n_products": [20]},
                         index=pd.Index(["대원산업"], name="name_key"))
    factories = _frame([["대원산업(주)", "대원산업"]], ["company_name", "name_key"])
    r = _row(_xwalk(_targets("대원산업"), factories=factories, factory_stats=stats), "kicox_factories", "대원산업")
    assert (r["status"], bool(r["use"])) == ("검수 필요", True)
    assert "전국 공장 25곳" in r["note"]


def test_factory_below_threshold_is_confirmed():
    stats = pd.DataFrame({"n_factories": [19], "n_sido": [3], "n_products": [4]},
                         index=pd.Index(["가상화학"], name="name_key"))
    factories = _frame([["가상화학", "가상화학"]], ["company_name", "name_key"])
    r = _row(_xwalk(_targets("가상화학"), factories=factories, factory_stats=stats), "kicox_factories", "가상화학")
    assert r["status"] == "확정"


# ---- 덮어쓰기 ----

def _overrides(rows):
    return _frame(rows, ["source", "source_name", "company_id", "reason"])


def _base_xwalk():
    return _xwalk(_targets("가상화학", "케이씨씨"),
                  emission=_frame([["가상화학", "가상화학"]], ["company_name", "name_key"]))


def test_override_none_excludes_link():
    xw, problems = match.apply_overrides(_base_xwalk(), _overrides([["ngms_emission", "가상화학", "NONE", "다른 회사"]]),
                                         _targets("가상화학", "케이씨씨"))
    r = _row(xw, "ngms_emission", "가상화학")
    assert (r["status"], bool(r["use"]), r["method"]) == ("제외", False, "수동")
    assert problems.empty


def test_override_adds_link_for_different_spelling():
    xw, _ = match.apply_overrides(_base_xwalk(), _overrides([["kicox_factories", "KCC(주)", "케이씨씨", "영문 표기"]]),
                                  _targets("가상화학", "케이씨씨"))
    r = _row(xw, "kicox_factories", "KCC")
    assert (r["company_id"], r["status"], bool(r["use"]), r["method"]) == ("케이씨씨", "확정", True, "수동")


def test_override_reassigns_existing_link():
    xw, _ = match.apply_overrides(_base_xwalk(), _overrides([["ngms_emission", "(주)가상화학", "케이씨씨", "확인함"]]),
                                  _targets("가상화학", "케이씨씨"))
    assert _row(xw, "ngms_emission", "가상화학")["company_id"] == "케이씨씨"


def test_override_with_unknown_company_is_reported_not_applied():
    base = _base_xwalk()
    xw, problems = match.apply_overrides(base, _overrides([["ngms_emission", "가상화학", "없는회사", "오타"]]),
                                         _targets("가상화학", "케이씨씨"))
    assert _row(xw, "ngms_emission", "가상화학")["company_id"] == "가상화학"
    assert problems["category"].tolist() == ["덮어쓰기 오류"]


# ---- 검수 목록 ----

def test_review_queue_lists_each_category():
    targets = _targets("대원산업", "신규회사")
    stats = pd.DataFrame({"n_factories": [58], "n_sido": [11], "n_products": [54]},
                         index=pd.Index(["대원산업"], name="name_key"))
    xw = _xwalk(targets, factories=_frame([["대원산업", "대원산업"]], ["company_name", "name_key"]),
                factory_stats=stats,
                prev=_frame([["대원산업", "대원산업", 2025]], ["name_key", "company_name", "disclosure_year"]))
    current = _frame([["Google", "GOOGLE", None]], ["company_name", "name_key", "industry"])
    problems = _frame([["덮어쓰기 오류", "없는회사", None, "ngms_emission", "대상에 없음"]], match.REVIEW_COLUMNS)
    review = match.review_queue(targets, xw, current, problems, prev_year=2025)
    assert review.columns.tolist() == match.REVIEW_COLUMNS
    assert review.groupby("category").size().to_dict() == {
        "공장 동명 의심": 1, "전년 공시와 이름 불일치": 1, "업종 결측": 1, "덮어쓰기 오류": 1}
    assert review.loc[review["category"] == "전년 공시와 이름 불일치", "company_id"].tolist() == ["신규회사"]


def test_read_manual_csv_handles_header_only_and_missing_file(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("source,source_name,company_id,reason\n", encoding="utf-8")
    cols = ["source", "source_name", "company_id", "reason"]
    assert match.read_manual_csv(p, cols).columns.tolist() == cols
    assert match.read_manual_csv(tmp_path / "none.csv", cols).empty


# ---- 원본 회귀 (conftest의 sources: 원본이 없으면 건너뜀) ----

@pytest.fixture(scope="module")
def raw_result(sources):
    from pipeline.sources import kisa
    d = sources.disclosure
    targets = kisa.select_targets(d, 2026, "제조업")
    xw = match.build_xwalk(targets, prev_year=2025, prev=d[d["disclosure_year"] == 2025],
                           membership=sources.membership, jurir=sources.jurir, emission=sources.emission,
                           factories=sources.factories, factory_stats=sources.factory_stats)
    review = match.review_queue(targets, xw, d[d["disclosure_year"] == 2026],
                                pd.DataFrame(columns=match.REVIEW_COLUMNS), prev_year=2025)
    return xw, review


def test_raw_link_counts(raw_result):
    xw, _ = raw_result
    used = xw[xw["use"].astype(bool)]
    assert used.groupby("source").size().to_dict() == {
        "kisa_2025": 351, "ftc_affiliates": 131, "ngms_emission": 145, "kicox_factories": 353}
    assert int((xw["method"] == "영문 표기 변환").sum()) == 28


def test_raw_review_counts(raw_result):
    _, review = raw_result
    assert review.groupby("category").size().to_dict() == {
        "공장 동명 의심": 4, "전년 공시와 이름 불일치": 36, "업종 결측": 6}
