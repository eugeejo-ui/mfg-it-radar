# 데이터 결합 스키마 — 제조업 IT 투자 레이더

## 0. 이 문서의 용도

- 원본 데이터 7종(DART 포함)이 회사를 어떻게 식별하는지, 어떤 경로로 한 회사에 모이는지 정리함
- 결합 후 회사 1곳당 확보되는 정보와 제조업 387개사 기준 확보 수를 적음
- 6장은 M1에서 실제로 만든 정제 결과 테이블이고, 7장은 M3 이후 추가·변경할 테이블임
- 수치는 2026-09-28 원본 파일 기준임
  - 2장의 결합 수는 기획 단계 점검값(이름키 완전 일치)임
  - 5·6장의 수치는 M1 빌드 결과(완전 일치 + 영문 표기 변환 + 수동 보완)임
- 회사명 정규화는 SPEC 7장 규칙 + 영문 대문자화임. 원본별 형식은 `docs/data-sources.md`

## 1. 연결 구조

모든 원본에 공통으로 들어 있는 키는 없음. DART 고유번호(corp_code)를 기업 마스터의 기본키로 두고, 나머지 원본을 네 가지 경로로 붙임. corp_code가 생기기 전(M1·M2)에는 임시 식별자 `company_id` = KISA 이름키를 씀 (6장).

```
[정확 결합]  키 값이 같으면 같은 회사
  공정위 기업집단별 개요 ──기업집단명──▶ 공정위 소속회사 개요 ──법인등록번호 = jurir_no──▶ 기업 마스터

[이름 결합]  회사명 정규화 → 대응표(사람 검수) → company_id (M3부터 corp_code)
  KISA 정보보호 공시 (연도별) ────────▶ 기업 마스터
  NGMS 배출권 할당대상 ──────────────▶ 기업 마스터
  산단공 전국 등록공장 (회사당 N행) ───▶ 기업 마스터

[DART 조회]  corp_code로 API 호출 (M3~)
  기업 마스터 ──▶ 기업개황 · 재무 · 공시목록 · 직원현황

[지역]  기업 키 없음, 시도 단위로만 연결 (보류)
  산단공 등록공장의 시도 ──시도──▶ 산단공 시도별 통계 4종
```

## 2. 원본별 식별자

| 원본 | 한 행의 단위 | 자체 키 | 결합에 쓰는 필드 | 연결 방식 | 기획 단계 결합 수 | 위험 |
|---|---|---|---|---|---|---|
| KISA 정보보호 공시 2025·2026 | 회사 × 공시연도 | 없음 | 기업명 | 이름 | 2025↔2026 이름 일치 737 / 826 | 법인번호가 없음. 회사명이 바뀌면 연도 간 연결이 끊김 |
| 공정위 소속회사 개요 | 회사 × 소속 집단 | 법인등록번호 (13자리, 결측 0) | 법인등록번호, 사업자등록번호(10자리), 소속회사명 | 정확 (DART jurir_no) | 정보보호와 이름 일치 290 (제조업 125) | 18개사가 두 집단에 동시 소속 (예: 애경산업은 태광·애경, 씨텍은 롯데·엘지). 이름키가 같은 서로 다른 법인 2쌍('동림', '동양에너지') |
| 공정위 기업집단별 개요 | 기업집단 | 기업집단명 | 기업집단명 | 정확 (소속회사 개요와 집단명 102개 완전 일치) | 102 | 상장·비상장 소속회사수 열이 전부 0 |
| NGMS 배출권 할당대상 | 업체 | 업체코드 (I·E·M·F·S 등으로 시작하는 11자리 문자, NGMS 내부용) | 업체명, KSIC 5자리 | 이름 | 정보보호 186 (제조업 142), 소속회사 239 | 업체코드가 다른 원본에 없어 결합에 못 씀 |
| 산단공 전국 등록공장 | 공장 | 없음 (순번은 행 번호) | 회사명, 공장주소 | 이름 | 정보보호 제조업 334 | 동명 회사가 섞임. '대원산업' 한 이름에 공장 58곳·11개 시도·생산품 54종 |
| 산단공 시도별 통계 4종 | 시도 | 시도 | 시도 | 지역 단위 | — | 공장규모 파일은 라벨이 뒤바뀐 것으로 보임. 파일마다 지역 구분이 다름 |
| DART OpenAPI | 회사 | corp_code (8자리) | jurir_no, bizr_no, corp_name, stock_code | 허브 | 미측정 | 재무 API는 정기보고서 제출사 위주 |

## 3. 기본키를 corp_code로 두는 이유

- DART 자동 갱신에 쓰는 API(기업개황, 재무, 공시검색, 직원현황)가 모두 corp_code로 조회함
- 기업개황의 jurir_no(법인등록번호)로 공정위 소속회사와 정확히 이어짐
- 회사명이 바뀌어도 corp_code는 유지됨. 대상 387곳 중 36곳은 2025 공시와 이름이 달라 연도 간 연결이 끊기는데, 이 가운데 이름만 바뀐 회사는 corp_code로 다시 이어짐
- 공개해도 되는 식별자라 기업 브리프 주소(`?corp=`)에 쓸 수 있음. 법인등록번호·사업자등록번호는 SPEC 5장에 따라 결합에만 쓰고 화면에 노출하지 않음

## 4. 이름 결합 규칙 (M1 구현)

- 이름키 완전 일치가 먼저임
- 완전 일치가 없으면 "영문 표기 변환" 키로 맞춤
  - 이름키의 영문 글자를 한글 발음으로 바꾼 키 (예: `CJ제일제당` → `씨제이제일제당`, `LG전자` → `엘지전자`)
  - 원본마다 영문·한글 표기가 섞여 있어 대기업 계열사가 빠지는 문제를 막음
  - M1 빌드에서 28건이 이 규칙으로 붙었고, 모두 같은 회사의 다른 표기임을 확인함
- 비슷한 이름 추정(유사도 매칭)은 하지 않음. 놓친 결합은 `data/manual/xwalk_overrides.csv`로 보완함 (자동 결합보다 항상 우선)
- 원본별 상태
  - 공정위에서 같은 이름키에 법인등록번호가 둘 이상이면 검수 필요로 두고 결합하지 않음
  - 공장은 이름 하나에 전국 공장이 20곳 이상이면 검수 필요(동명 의심)로 두되 결합은 함 → 화면에 동명 가능성을 표시함
- 정보보호 공시를 corp_code에 붙이는 경로 (M3)
  - 경로 1: 정보보호 이름 = 소속회사 이름 → 법인등록번호 → DART jurir_no → corp_code
    - 대상 131곳 (영문 표기 변환 포함)
    - 비교 대상이 3,521개사로 좁아 동명 오결합 위험이 낮음
  - 경로 2: 정보보호 이름 = DART corp_name → corp_code
    - 나머지 256곳
    - DART 법인 전체와 비교하므로 동명 후보가 여럿 나올 수 있음 → 상장 여부, 제조업 업종코드(10~34), 본사 주소로 좁히고 사람이 검수함

## 5. 회사 1곳당 파악 가능한 정보

제조업 387개사 기준. "M1"은 현재 빌드 결과, "DART"는 M3 이후 채워지는 항목임.

| 영역 | 항목 | 출처 | 387곳 중 확보 (M1) |
|---|---|---|---|
| 기본 | 회사명, 업종 대분류, 임직원 수와 규모 구간 | KISA | 387 |
| 기본 | 세부업종 (KSIC 중분류) | 공정위 업종코드 → 배출권 KSIC → (DART 업종코드) | 191 (공정위 131·배출권 60), 나머지 DART |
| 기본 | 상장 여부 | 공정위 기업공개일 → (DART 법인구분) | 131 (이 중 상장 123), 나머지 DART |
| IT 여력 | IT 투자액, 전년 대비 증감률 | KISA 2025·2026 | 투자액 387, 증감 351 |
| IT 여력 | IT 인력, IT 인력 비중 | KISA | 383 |
| IT 여력 | IT 투자/매출 | KISA ÷ 개별 기준 매출 | M4 (기준 연도 확인 후) |
| 보안 성숙도 | 보안 투자액과 비중(B/A), 보안 내부·외부 인력, CISO·CPO 임원·겸직·직책·활동 건수, 사전점검, 투자우수기업 | KISA | 387 |
| 보안 성숙도 | 보유 인증 (알려진 인증을 인식한 것) | KISA | 127 |
| 투자 품목 | 주요 투자항목 원문 | KISA | 216 (자리표시·"첨부 참조" 제외) |
| 구매 경로 | 기업집단명(최대 2곳), 집단 순위·규모, 같은 집단의 계열 SI 회사명 | 공정위 2종 + 수동 보완 | 131 (계열 SI 보유 집단 소속 72) |
| 규제 노출 | 배출권 할당대상 여부, KSIC | NGMS | 145 |
| 생산 거점 | 공장 수, 시도·시군구, 산업단지 입주 공장 수, 대표 생산품 | 산단공 | 340 (동명 의심 4 포함) |
| 재무 | 매출·영업이익·당기순이익·자산 1개년 (개별) | 공정위 | 131 |
| 재무 | 매출·영업이익 3개년 (연결·개별 구분) | DART | DART |
| 최근 공시 | 보고서명, 접수일, 원문 링크 | DART | DART |
| 지역 맥락 | 공장 소재 시도의 업종별 공장 수 등 | 산단공 시도별 통계 | 보류 |
| 결합 전용 (비노출) | 법인등록번호, 사업자등록번호, 대표자 | 공정위, DART | — |

## 6. 정제 결과 테이블 (M1 구현, `data/processed/`)

`python -m pipeline.jobs.annual`로 만듦. 모든 테이블은 `company_id`로 이어짐. 금액은 원 단위(`*_krw`).

| 테이블 | 한 행 | 키 | 행 수 | 주요 열 |
|---|---|---|---|---|
| company | 대상 회사 | company_id | 387 | company_name, industry, ksic2·ksic2_source·ksic2_label, size_band, employees, it_invest_krw, it_invest_prev_krw, it_yoy_pct, it_staff_ratio_pct, sec_invest_ratio_pct, ciso_exec, ciso_concurrent, uses_external_sec_staff, certs, has_cert, items_in_attachment, group_names, in_group, si_companies, group_has_si, listed, emission_target, factory_count, factory_sido, factory_sido_count, multi_sido, complex_factory_count, top_products, factory_homonym_suspect, signals |
| kisa_disclosure | 회사 × 공시연도 | (disclosure_year, name_key) | 1,599 | KISA 전 열 정제본, figures_in_attachment, items_in_attachment, certs, company_id(대상 회사만) |
| group_membership | 회사 × 소속 집단 | (group_name, company_name) | 3,539 | disclosure_ym, industry_code, ksic2, employees, established·affiliated_on·listed_on, listed, 금액 6종, fs_div=OFS, company_id |
| business_group | 기업집단 | group_name | 102 | rank, n_affiliates, employees, 금액 6종, si_companies, has_si |
| emission_target | 배출권 업체 | company_code | 772 | company_name, ksic5, ksic2, company_id |
| factory | 대상 회사와 결합된 공장 | seq | 1,389 | company_id, company_name, complex_name, in_complex, products, sido, sigungu, homonym_suspect |
| xwalk | (원본, 이름키) | (source, name_key) | 980 | source_name, company_id, method(이름 일치·영문 표기 변환·수동), status(확정·검수 필요·제외), use, note |
| source_meta | 원본 | source_id | 6 | provider, portal_url, reference_date, rows, note, built_at |

- `company_id`: M1·M2에서는 KISA 이름키임. M3에서 `pipeline/build.py`의 `assign_company_id`만 corp_code로 바꾸고, 앱은 `company_id`만 씀
- `review_queue.csv`: 사람이 볼 검수 목록. 분류는 공장 동명 의심, 공정위 이름 충돌, 전년 공시와 이름 불일치, 업종 결측, 덮어쓰기 오류임
- 법인등록번호는 `data/cache/ftc_jurir.parquet`(gitignore)에만 있음. processed 파일은 개인정보 검사를 거쳐야 쓰임
- 사람이 고치는 파일
  - `data/manual/xwalk_overrides.csv`: source, source_name, company_id(또는 NONE), reason
  - `data/manual/si_manual.csv`: group_name, company_name, reason. 현재 에스케이(주), (주)포스코디엑스 2건 (SPEC 7장)

## 7. M3 이후 추가·변경할 테이블

| 테이블 | 한 행 | 키 | 주요 열 | 단계 |
|---|---|---|---|---|
| company (변경) | 대상 회사 | corp_code | + stock_code, corp_cls, 본사 시도, DART 업종코드 | M3 |
| xwalk (변경) | (원본, 이름키) | (source, name_key) | company_id가 corp_code로 바뀜, method에 "법인번호" 추가 | M3 |
| financial | 회사 × 사업연도 × 재무 기준 | (corp_code, bsns_year, fs_div) | revenue, op_income, net_income, assets, source | M4 |
| filing | 공시 1건 | rcept_no | corp_code, rcept_dt, report_nm, signal_type | M5 |
| region_stat | 시도 × 항목 × 기준일 | (sido, item, 기준일) | value | 필요 시 |

- financial의 fs_div(연결 CFS / 개별 OFS)로 재무 기준을 구분함. 공정위 매출은 개별(OFS)임. 한 비율 계산에 두 기준을 섞지 않음 (SPEC 5장)

## 8. 결합 품질 주의

- 공장: 동명 의심 4곳(대원산업 58, 우리산업 31, 태광산업 31, 에스텍 23)은 결합하되 표시함. M3에서 본사 시도와 공장 시도를 비교해 확정함
- 영문 약어만으로 붙은 공장 결합(DYP↔디와이피, TSE↔티에스이)은 동명 가능성이 있어 M3에서 다시 확인함
- 공정위 주업종이 제조업이 아닌 대상 5곳(도매·소매·전문서비스 등)이 있음. 세부업종 벤치마크(M4)에서 그대로 쓸지 정해야 함
- 소속회사 매출액 "0" 600행은 값 없음으로 저장함 (대상과 결합된 소속회사는 모두 매출이 0보다 큼)
- 정보보호 공시 2026: 업종이 비어 있는 행 6개(글로벌 IT 기업), 임직원 수가 소수로 적힌 행 652개(규모 구간은 반올림)

## 9. DART 결합 전에 측정할 것 (M3)

- DART 고유번호 목록(corpCode.xml)을 받아 대상 387곳의 corp_code 결합률 측정
- 공정위 소속회사 3,521개사의 법인등록번호와 DART jurir_no 일치율 측정
- DART 재무 API가 공정위 밖 대상 256곳 중 몇 곳의 매출을 주는지 확인
