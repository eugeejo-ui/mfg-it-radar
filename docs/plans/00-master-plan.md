# 제조업 IT 투자 레이더 — 전체 구축 계획

## Context

- SPEC.md(기업 IT 투자 레이더)를 바탕으로 공개 웹서비스를 만듦. 원본 파일 5종 + 산단공 CSV 5종을 직접 점검한 결과, 공정위·배출권·공장 데이터는 제조업에서만 의미 있게 결합됨 → 주제를 "제조업 IT 투자 레이더"(정보보호 공시 제조사 387곳)로 좁힘
- 결합 구조는 `docs/data-schema.md`로 정리함: 기본키 = DART corp_code, 공정위는 법인등록번호로 정확 결합, 정보보호 공시·배출권·공장은 이름 결합 + 사람 검수
- 사용자가 DART OpenAPI로 자동 갱신되는 서비스를 원함 → 파일 기반 연 1회 갱신 위에 DART 일·월 단위 자동 수집을 얹는 구조로 설계함
- 결과물: GitHub 저장소 + Streamlit Community Cloud 공개 앱. 최근 공시는 매일, DART 재무·기업개황은 매월 자동 갱신됨

## 1. 확정된 결정

| 항목 | 결정 |
|---|---|
| 프로젝트 폴더 | `C:\mfg-it-radar` (생성함, 세션 작업 위치를 이곳으로 옮김) |
| 서비스명 (가칭) | 제조업 IT 투자 레이더 (설정값 1개로 교체 가능) |
| 대상 | 2026 정보보호 공시 제조업 387개사. 대상 목록은 테이블로 관리하고 387을 코드에 고정하지 않음 (2027 공시부터 상장사 전체로 확대 예정) |
| 주 사용자 | IT 솔루션 발굴 영업 전반. 기업 브리프 블록 순서는 SPEC 4.1 그대로 |
| 화면 구조 | 상단 탭 3페이지: 후보 목록(첫 화면) · 기업 브리프(`?corp=` 주소) · 데이터 출처. 브리프에 목록 이전·다음 이동 |
| SPEC 대비 추가 | 공장 소재 시도를 후보 목록의 필터·열로 추가 |
| 화면 디자인 | 사용자가 Stitch로 진행함. M2 시작 시 그때까지의 진행 상황·맥락을 정리한 Stitch용 프롬프트와 md 파일을 만들어 넘김. 확정된 디자인은 받아서 Streamlit으로 구현함 |
| 기본키 | DART corp_code (8자리) |
| 데이터 | 실데이터 사용. 가상 데이터는 테스트 fixture로만 씀 (앞서 정한 "샘플 데이터 화면"은 원본 파일 확보로 대체) |
| 저장 | 정제 결과 parquet을 저장소에 커밋. 원본 파일은 커밋하지 않음 |

## 2. 시스템 구성

```
[연 1회, 로컬 실행]  원본 파일 (KISA · 공정위 · NGMS · 산단공)
      └─ pipeline annual build: 정제 → 결합(대응표 + 검수) → data/processed/*.parquet → git push
[매일, GitHub Actions]  DART 공시검색 → 추적 대상 corp_code만 거름 → filing parquet → git push
[매월, GitHub Actions]  DART 고유번호 · 기업개황 · 재무 · 직원현황 → parquet → git push
                        + 원본 새 버전 감지(공정위 공개년월 등) → 검수 필요 목록을 GitHub 이슈로 올림
[상시]  Streamlit Community Cloud: data/processed만 읽는 읽기 전용 앱 (push 시 자동 반영, 앱 서버에 API 키 없음)
```

- 원본 파일이 필요한 연간 재구축은 관리자 PC에서 실행함. Actions는 원본 없이 processed 테이블과 대응표만으로 DART 증분 수집을 함
- 법인등록번호는 연간 로컬 빌드에서 결합 확인용으로만 쓰고 커밋하지 않음 (공개 저장소 = 공개)

## 3. 저장소 구조

```
app/
  streamlit_app.py          st.navigation 상단 탭, 공통 헤더·출처 기준일
  pages/candidates.py  brief.py  sources.py
  blocks/                   브리프 블록별 1파일 (it_capacity, purchase_path, security, items, benchmark, regulation, sites, filings, financials)
  charts.py                 seaborn 그래프
  data_access.py            parquet 로드, st.cache_data(키 = build_id)
  format.py                 억원·%·증감 표기, 값 없음 / 0 / 공시 원문 참조 구분
pipeline/
  sources/kisa.py ftc.py ngms.py factory.py region.py    원본별 읽기·정제
  dart/client.py corpcode.py company.py financial.py filings.py employees.py
  normalize.py  match.py  peers.py  signals.py  build.py  validate.py  meta.py
  jobs/annual.py daily.py monthly.py
data/
  raw/            gitignore. manifest.csv(파일명, 출처 URL, sha256, 기준일)만 커밋
  manual/         xwalk_overrides.csv(사람이 편집, 항상 우선), si_manual.csv(업종코드로 안 잡히는 SI 보완)
  processed/      company, xwalk, security_disclosure, group_membership, business_group,
                  emission_target, factory, financial, filing/YYYY-MM, region_stat, source_meta
docs/  spec/SPEC.md  data-schema.md  stitch/(Stitch용 프롬프트·맥락 md, M2에서 생성)  plans/(단계·작업 계획서, 10장)
tests/  fixtures/(DART 응답 JSON, 키 제거)  test_*.py
.github/workflows/  ci.yml  daily.yml  monthly.yml
.streamlit/config.toml   requirements.txt(앱, 버전 고정)   requirements-pipeline.txt
```

## 4. 데이터 파이프라인

### 4.1 정제 규칙
- 회사명 정규화: SPEC 7장 정규식 + 영문 대문자화 (점검 스크립트에서 검증함)
- 금액: KISA는 원 → 억원 표시. 공정위는 쉼표 문자열·백만원 → 숫자. 공정위 매출 "0"(600행)은 값 없음으로 저장
- KISA "첨부 참조" 행: `attachment_only = True`, 화면은 "공시 원문 참조"
- 업종 표기 `제조업(10~34)` → "제조업". 업종 결측 6행은 검수 목록으로
- 규모 구간: KISA 총임직원 기준 (387곳 모두 있음, 소수 기재는 반올림). ≤300 / 300~1,000 / 1,000~3,000 / >3,000
- 상장 여부: 공정위 기업공개일 → 없으면 DART corp_cls (공정위 `구분` 열은 상장 여부가 아님)
- 개인정보: 대표자·사업자등록번호·전화번호는 읽을 때 버림. 법인등록번호는 로컬 빌드 메모리에서만 씀

### 4.2 결합 (corp_code 부여)
1. DART corpCode.xml(전체 법인 목록) 이름키 ↔ 정보보호·배출권 이름키 → 후보 corp_code
2. 후보만 기업개황(company.json) 조회 (약 600회) → jurir_no·주소·업종코드·상장 여부 확보
3. 확정 규칙
   - 공정위 소속회사와 이름이 맞는 125곳: 공정위 법인등록번호 = jurir_no이면 확정
   - 나머지: 후보가 1개이고 업종코드가 제조업(10~34)이면 확정. 후보가 여럿이면 상장사 → 본사 주소 순으로 좁히고, 그래도 여럿이면 검수
4. `xwalk_overrides.csv`(corp_code 또는 NONE)가 자동 결과보다 항상 우선함. 확정된 대응은 다음 해에 재사용함
5. 공장: 이름이 전국에서 유일하거나, 공장 시도가 DART 본사 시도와 겹칠 때만 결합함. 공장 20곳 이상이거나 생산품이 업종과 동떨어지면 "동명 가능"으로 표시하고 검수함
6. 계열 SI: 같은 기업집단에서 업종코드가 J620으로 시작하는 회사 + `si_manual.csv`
7. 회사↔기업집단은 다대다(두 집단에 속한 회사 18곳)로 group_membership에 그대로 담음

### 4.3 DART 수집

| 데이터 | API | 호출 단위 | 쓰임 |
|---|---|---|---|
| 법인 목록 | corpCode.xml (zip) | 1회 | 이름 후보, 회사명 변경 추적 |
| 기업개황 | company.json | 회사 1곳당 1회 | jurir_no(결합 전용), KSIC 세부업종, 상장 구분, 본사 주소 |
| 재무 | fnlttMultiAcnt.json | 최대 100곳/회, 사업보고서 1건에 3개년 | 매출·영업이익, fs_div로 연결/개별 구분 |
| 직원 | empSttus.json | 회사 1곳당 1회 | 보조 규모 지표 (행 합산) |
| 공시 | list.json | 날짜 구간 전체 조회(3개월 이내), 100건/페이지 | 최근 90일 신호 |

- 호출 한도: 약 2만 건(020 오류). 초기 적재 약 1.4~1.8천 건, 매일 50~200건으로 한도의 10% 미만
- 재무 API는 상장사와 사업보고서 제출 비상장사만 커버함. 감사보고서만 내는 회사는 재무가 비어 "DART 재무 미제공"으로 표시함
- 공시 신호: 공시 유형 B(주요사항)·I(거래소). 보고서명 키워드로 분류함: 신규시설투자, 유형자산 양수, 타법인 주식 취득, 합병, 분할, 영업양수. `[기재정정]`과 비고 "정"은 원 공시에 연결함. 원문 링크는 `https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}`

### 4.4 파생 지표
- IT 여력: IT 투자액, 전년 대비 증감(2025·2026 모두 0보다 클 때만), IT 인력 비중(C/총임직원), IT 투자/매출(개별 매출만 사용, 사업연도 일치)
- 벤치마크(`peers.py`): 세부업종 × 규모 구간 → 10곳 미만이면 규모 조건을 풂 → 그래도 10곳 미만이면 제조업 전체. 실제 적용한 조건과 N을 반환함. IT 투자/매출은 매출이 있는 회사끼리만 비교하고 N을 따로 셈
- 후보 목록 신호 태그(고정 순서): IT 투자 +20%, CISO 겸직, 외부 보안인력, 인증 없음, 계열 SI 없음, 배출권 할당대상, 2개 이상 시도, 최근 90일 공시
- 점수·순위는 만들지 않음 (SPEC 5장)

### 4.5 검증 게이트 (쓰기 전에 실패하면 중단)
- 키 고유성(corp_code, rcept_no 등), 필수 열 존재, 행 수가 직전보다 20% 넘게 줄지 않음
- 결합 수 회귀 기준(2026 파일 기준): 정보보호 제조업 387, 증감 계산 351, 공정위 이름 일치 125, 배출권 142, 공장 334(동명 규칙 적용 전)

## 5. 자동 갱신

| 작업 | 주기·시각 | 내용 | 실패 시 |
|---|---|---|---|
| daily.yml | 매일 06:17 KST (cron `17 21 * * *`) | 최근 7일 공시 재조회 → rcept_no 기준 upsert → 월별 파일 → 바뀐 게 있을 때만 커밋. source_meta 갱신 | 한 페이지라도 3회 재시도 후 실패하면 쓰지 않음(다음 날 7일 재조회로 메움). 020 한도 초과: 즉시 중단. 800 점검: 조용히 넘어감. 010/011/012 키 오류: 이슈 생성 |
| monthly.yml | 매월 2일 | corpCode 갱신(회사명 변경), 대상 기업개황, 새 사업연도 재무·직원(4월 이후), 원본 새 버전 감지, 결합 실패·동명 의심 목록을 이슈로 올림 | 위와 같음 |
| ci.yml | push·PR | pytest, 앱 스모크 테스트 | — |
| 연간 수동 | 공정위 5월, KISA 7~8월, NGMS·산단공 게시 시 | 원본 교체 → `python -m pipeline.jobs.annual` 로컬 실행 → 검수 → 커밋 | — |

- 세 작업은 같은 concurrency 그룹으로 묶고, push 전에 `git pull --rebase`를 함
- 공개 저장소의 예약 실행은 60일 동안 활동이 없으면 꺼짐 → daily의 source_meta 커밋이 활동 기록 역할을 함
- 앱 캐시는 build_id(processed 갱신 시각)를 키로 씀. push 후에도 예전 데이터가 남는 문제를 막음
- 데이터 신선도 표시: 모든 블록에 출처·기준일 캡션. DART 공시 확인 시각이 3일을 넘기면 상단에 안내함

## 6. 화면

- 화면 디자인은 사용자가 Stitch로 진행함. M2 시작 시 `docs/stitch/`에 두 파일을 만들어 넘김
  - Stitch에 바로 붙여 넣을 프롬프트
  - 맥락 md: 그때까지의 진행 상황, 확정된 결정, 화면별 요구사항, 실제 데이터 예시·빈 값 사례, 아래 방향, SPEC 12장 디자인 지침, Streamlit으로 옮길 때의 제약(상단 탭, 사이드바 필터, 표 위젯, seaborn 그래프 이미지 등)
- Stitch 결과(화면 이미지·코드)를 받으면 `.streamlit/config.toml` 테마와 최소한의 CSS로 Streamlit에 옮김. Streamlit으로 재현하기 어려운 부분은 대안을 제시하고 확인받음
- 방향 (맥락 md에 담아 Stitch에 전달함)
  - 강조는 IT 여력 블록 한 곳에만 씀. 증감은 ▲▼와 부호로만 나타냄 (한국은 빨강이 상승이라 색 관례가 충돌함)
  - 숫자는 오른쪽 정렬, 고정폭 숫자, 단위는 열 제목에 씀
  - 블록은 카드 대신 구분선으로 나눔
  - 기본 정렬은 회사명순 (순위처럼 보이지 않게)
- 후보 목록: 사이드바 필터(업종 세부, 규모, IT 증감, CISO 겸직, 외부인력, 인증 보유·미보유, 계열 SI, 배출권, 다거점, 공장 시도, 90일 공시) → 표(회사명, 세부업종, 규모, 공장 시도, IT 투자액, 증감률, 신호 태그) → 행 선택 시 브리프로 이동. 결과가 0곳이면 "조건 X를 풀면 N곳"을 안내함. CSV는 utf-8-sig
- 기업 브리프: SPEC 4.1 블록 10개. 블록마다 값 없음 / 0 / 공시 원문 참조 / 결합 못 함 / 해당 없음 문구를 구분함
- 데이터 출처: source_meta 표(기관, 기준일, 다음 갱신 예상, 알려진 한계) + 결합 방식과 오결합 가능성 고지
- 한글 폰트: 앱 UI와 seaborn이 같은 서체를 쓰게 함. Cloud에서는 `packages.txt`(fonts-nanum) 또는 번들 폰트로 해결함 (Stitch 디자인의 서체를 보고 정함)

## 7. 마일스톤

| 단계 | 내용 | 완료 기준 |
|---|---|---|
| M0 준비 | `C:\mfg-it-radar`(생성함)에 git init, SPEC.md·data-schema.md·원본 파일 이관, CLAUDE.md에 문서 규칙 기록, 파이썬 환경 준비, GitHub 저장소 생성(gh CLI 로그인 확인됨, 이름·공개 여부는 실행 전 확인). 사용자가 OpenDART 키 발급 신청(본인 직접) | 폴더·저장소 준비, 키 신청 완료 |
| M1 원본 정제 | sources/*, normalize, 원본별 정제 parquet, 이름 결합(DART 없이), 회귀 테스트 | 4.5 결합 수 테스트 통과 |
| M2 화면 v0 | Stitch 핸드오프(진행 상황·맥락 브리핑, `docs/stitch/`에 프롬프트와 맥락 md 생성) → 사용자가 Stitch에서 디자인 확정 → 결과를 받아 DART 없이 가능한 블록(IT 여력, 보안, 투자 품목, 구매 경로, 규제, 생산 거점, 출처)과 후보 목록을 Streamlit으로 구현 → Cloud 조기 배포 | Stitch 디자인 확정, 로컬·Cloud에서 3페이지 동작 |
| M3 DART 결합 | client(주입 가능한 세션, 재시도, 상태 코드 처리), corpCode → 후보 → 기업개황 → 검수 루프, corp_code 기본키로 전환 | 387곳 corp_code 결합률 보고, 검수 목록 처리 |
| M4 재무·벤치마크 | 재무·직원 수집, 세부업종 채움, peers.py, 벤치마크 블록, IT 투자/매출 | 벤치마크 확대 규칙 테스트 통과, 화면에 N 표시 |
| M5 공시·일 갱신 | 90일 공시 초기 적재, 신호 분류, daily.yml, 신선도 표시 | Actions 수동 실행 1회 성공 → 커밋 → 앱 반영 |
| M6 월 갱신·마감 | monthly.yml, 이슈 자동 생성, 검증 게이트, 출처 페이지 마감 | 한 달 무인 운영 |

- 단계·작업마다 상세 계획서를 먼저 쓰고, 마친 뒤 결과를 적음 (10장)
- M3가 핵심 경로임(사람 검수 대기). 키가 늦게 나오면 M1·M2를 먼저 진행함

## 8. 검증 방법

- 단위 테스트(pytest, 표 형식)
  - 회사명 정규화, 금액 파싱(쉼표, "0" → 값 없음), 규모 구간 경계값
  - 벤치마크 확대 규칙 전 분기, 신호 키워드 분류(정정 공시 포함), rcept_no → URL
- 회귀 테스트: 4.5의 결합 수. 원본이 바뀌면 기준값을 갱신하고 기록함
- DART 클라이언트: 녹화한 JSON fixture(키 제거)로 테스트함. 실호출 테스트는 `-m live`로 분리해 수동으로만 돌림
- 앱: `streamlit.testing.v1.AppTest`로 3페이지를 fixture parquet에 대해 스모크 실행. `streamlit run app/streamlit_app.py` 후 브라우저 창에서 후보 목록 → 행 선택 → 브리프 → 이전·다음 → 출처 흐름을 직접 확인
- 자동 갱신: workflow_dispatch로 daily·monthly를 수동 실행 → 커밋 발생·미발생 확인 → Cloud 반영 확인
- 원칙 점검표: 점수 없음, 비교 대상 N 표시, 연결/개별 혼용 없음, 값 없음과 0 구분, 모든 블록 출처·기준일, 법인번호·대표자 비노출(processed 파일과 저장소 전체를 grep)

## 9. 사용자 확인·작업이 필요한 것

- OpenDART 회원가입과 API 키 발급: 본인이 직접 해야 함. 키는 GitHub Secrets(`DART_API_KEY`)와 로컬 `.env`(gitignore)에만 둠. 1인 1키라 유출되면 대체 키가 없음
- GitHub 저장소는 gh CLI(eugeejo-ui 계정 로그인 확인됨)로 만들되, 이름과 공개 여부를 실행 전에 확인받음
- Streamlit Community Cloud 연결은 사용자가 웹에서 GitHub 계정으로 로그인해 진행함 (M2 배포 시점)
- 무료 Cloud 앱은 12시간 동안 접속이 없으면 잠듦 → 첫 방문자가 깨우기 버튼을 눌러야 함 (알려진 한계로 출처 페이지에 적음)

## 10. 진행 문서 규칙

- 이 계획서는 승인 후 `docs/plans/00-master-plan.md`로 저장함
- 단계(M0~M6)를 시작하기 전에 단계 상세 계획서(`phase-plan.md`)를 새로 써서 저장함
- 단계 안의 작업(task)을 수행할 때도 작업 상세 계획서(`tasks/T<단계>.<번호>-<작업명>.md`)를 먼저 써서 저장함
- 단계·작업을 마치면 해당 계획서에 진행 과정, 결과, 다음 단계로 이어지는 내용(넘겨주는 산출물, 남은 문제, 다음 단계의 선행 조건)을 추가해 저장함
- 문서는 개조식 어미(~함, ~임)로 씀. SPEC 14장의 `docs/progress/` 기록은 이 문서들이 대신함
- 같은 규칙을 프로젝트 `CLAUDE.md`에 적어 다음 세션에서도 따르게 함

- 문서 종류·작성 시점·이름 규칙의 기준은 `docs/README.md`(문서 체계)이고, 양식은 `docs/plans/_templates/`에 있음

```
docs/
  README.md                       문서 체계
  spec/SPEC.md                    원본 명세 사본
  data-sources.md                 원본 데이터 참조 (엑셀 5개 상세)
  data-schema.md                  결합 스키마
  guides/                         사람이 따라 하는 절차 (DART 키 등)
  stitch/                         M2 Stitch 핸드오프
  plans/
    00-master-plan.md             전체 계획 (이 문서)
    _templates/                   단계·작업 계획서 양식
    M0-setup/
      phase-plan.md               단계 상세 계획 → 진행 기록 → 결과 → 다음 단계 연결
      tasks/T0.1-<작업명>.md       작업 상세 계획 → 진행 기록 → 결과 → 다음 작업 연결
    M1-source-cleaning/           원본 정제
    M2-screens-v0/                화면 v0
    M3-dart-matching/             DART 결합
    M4-financials-benchmark/      재무·벤치마크
    M5-filings-daily/             공시·일 갱신
    M6-monthly-hardening/         월 갱신·마감
```

| 문서 | 작업 전에 쓰는 부분 | 마친 뒤 덧붙이는 부분 |
|---|---|---|
| phase-plan.md | 목적, 이전 단계에서 넘겨받은 것, 범위·제외 범위, 작업 목록(ID·이름·산출물·상태), 완료 기준, 위험과 대응 | 진행 기록(날짜별), 결과(완료 기준 대비), 다음 단계로 이어지는 내용 |
| tasks/T*.md | 목적, 입력, 절차, 산출물, 검증 방법 | 진행 기록, 결과, 다음 작업으로 넘기는 것 |

- 상태 표기: 계획 / 진행 중 / 완료 / 보류

## 11. 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-09-28 | 전체 계획 승인. 프로젝트 폴더 `C:\mfg-it-radar` 생성. 진행 문서 규칙(10장) 추가 |
| 2026-09-28 | M2 화면 디자인을 사용자가 Stitch로 진행하도록 변경. `design-plan.md` 대신 `docs/stitch/`에 프롬프트·맥락 md를 만들어 넘김 |
| 2026-09-28 | 문서 체계 정비(T0.8): `docs/README.md`(문서 체계), `docs/data-sources.md`(엑셀 5개 등 원본 참조), 계획서 양식 추가. `CLAUDE.md`를 `/init` 형식으로 재작성 |
