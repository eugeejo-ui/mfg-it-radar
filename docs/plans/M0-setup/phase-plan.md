# M0 준비 — 단계 상세 계획서

- 상태: 완료 (사용자 작업 1건 남음: OpenDART 키 신청)
- 작성일: 2026-09-28
- 완료일: 2026-09-28
- 승인: 2026-09-28 (저장소 이름 `mfg-it-radar`, 공개 저장소로 확정)
- 상위 문서: `docs/plans/00-master-plan.md` 7장 M0

## 1. 목적

- M1부터 코드 작업을 바로 시작할 수 있게 작업 환경을 갖춤: 저장소, 문서, 원본 파일, 파이썬 환경, 코드 골격, 원격 저장소
- 다음 세션에서도 같은 규칙으로 이어서 작업하도록 프로젝트 규칙을 `CLAUDE.md`에 남김
- DART 키 발급처럼 사용자가 직접 해야 하는 일을 미리 시작시켜 M3에서 기다리지 않게 함

## 2. 이전 단계에서 넘겨받은 것

| 항목 | 위치 | 상태 |
|---|---|---|
| 서비스 명세 | `C:\Users\조유신\Downloads\SPEC.md` | 프로젝트 밖에 있음 → T0.2에서 사본을 둠 |
| 결합 스키마 | `docs/data-schema.md` | 프로젝트에 있음 |
| 전체 계획 | `docs/plans/00-master-plan.md` | 승인됨 (M2는 Stitch로 변경) |
| 원본 파일 10종 | `C:\Users\조유신\Downloads` | 점검 완료. 프로젝트 밖에 있음 → T0.3에서 복사 |
| 점검 수치 | 전체 계획 4.5 | M1 회귀 테스트 기준값으로 씀 |
| 도구 | Python 3.11.7(Anaconda), git 2.55, gh 2.100(eugeejo-ui 로그인, repo·workflow 권한) | 확인함 |

원본 파일 10종

| 구분 | 파일 |
|---|---|
| KISA | `2025_정보보호_공시_이행_기업리스트.xlsx`, `2026_정보보호_공시_이행_기업리스트.xlsx` |
| 공정위 | `소속회사 개요.xlsx`, `기업집단별 개요.xlsx` |
| NGMS | `배출권거래제 할당대상업체 현황_260101기준.xlsx` |
| 산단공 | `한국산업단지공단_전국등록공장현황_등록공장현황자료_20241231.csv`, 시도별 통계 4종(`…_시도별 공장규모/공장면적/공장상태/업종별 현황_20260831.csv`) |

## 3. 범위

포함
- git 저장소 초기화, `.gitignore`, `.gitattributes`, `README.md`
- 문서 이관(SPEC 사본), `CLAUDE.md` 작성
- 원본 파일을 `data/raw/`로 복사하고 `manifest.csv`(출처·기준일·sha256) 작성
- 가상환경 `.venv`, `requirements.txt`(앱), `requirements-pipeline.txt`(수집·정제·테스트), `.env.example`
- 빈 코드 골격(`app/`, `pipeline/`, `tests/`)과 pytest 설정, 원본 무결성 테스트 1개
- GitHub 원격 저장소 생성과 첫 푸시 (이름·공개 여부는 실행 직전 확인)
- OpenDART 키 발급·보관 안내 문서

제외 (다음 단계에서 함)
- 원본 정제·결합 코드, CI 설정(`ci.yml`) → M1
- 화면, Stitch 핸드오프 → M2
- DART 호출 → M3
- 자동 갱신 워크플로 → M5·M6

## 4. 작업 목록

각 작업은 시작 전에 `tasks/T0.x-<작업명>.md` 상세 계획서를 쓰고, 마친 뒤 결과를 덧붙임.

| ID | 작업 | 주요 산출물 | 상태 |
|---|---|---|---|
| T0.1 | 저장소 초기화 | `.git`(기본 브랜치 main), `.gitignore`, `.gitattributes`, `README.md` | 완료 |
| T0.2 | 문서 이관과 프로젝트 규칙 | `docs/spec/SPEC.md`, `CLAUDE.md` | 완료 |
| T0.3 | 원본 파일 이관과 목록 | `data/raw/` 10개 파일, `data/raw/manifest.csv` | 완료 |
| T0.4 | 파이썬 환경 | `.venv/`, `requirements.txt`, `requirements-pipeline.txt`, `.env.example` | 완료 |
| T0.5 | 코드 골격과 테스트 실행 확인 | `app/`, `pipeline/`(sources·dart·jobs), `tests/`, `pytest.ini`, `tests/test_raw_manifest.py`, `data/manual/`, `data/processed/` | 완료 |
| T0.6 | GitHub 저장소 생성과 첫 푸시 | 원격 저장소, 첫 커밋 | 완료 |
| T0.7 | OpenDART 키 발급·보관 안내 | `docs/guides/dart-api-key.md` | 완료 (발급은 사용자 작업) |

### 작업별 요점

T0.1 저장소 초기화
- `git init -b main`, 로컬 설정 `core.quotepath false`(한글 파일명을 그대로 보이게 함)
- `.gitignore`: `data/raw/*`(단 `manifest.csv`는 추적), `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.streamlit/secrets.toml`, `*.log`
- `.gitattributes`: `*.parquet binary`, 텍스트 줄바꿈 자동 처리
- `README.md`: 서비스 한 단락 설명, 문서 위치, 현재 단계만 적음 (실행 방법은 코드가 생기는 단계에서 추가)

T0.2 문서 이관과 프로젝트 규칙
- `Downloads\SPEC.md` → `docs/spec/SPEC.md` (원문 그대로, 변경 사항은 전체 계획 11장에 기록)
- `CLAUDE.md`에 담을 내용
  - 프로젝트 한 줄 설명과 문서 위치 (전체 계획, 스키마, SPEC)
  - 진행 문서 규칙: 단계·작업 계획서를 먼저 쓰고, 마친 뒤 진행 기록·결과·다음 단계 연결을 덧붙임. 개조식 어미
  - 데이터 원칙: 대표자·법인등록번호·사업자등록번호 비노출, 원본 파일·키 커밋 금지, 연결/개별 재무 혼용 금지, 값 없음과 0 구분, 점수·순위 없음
  - 작업 주의: 한글 경로 파일은 Git Bash·Python으로 다룸 (PowerShell 5.1 인코딩 문제 사례 있음), 가상환경 파이썬(`.venv\Scripts\python`)을 명시해서 씀
  - M2는 사용자가 Stitch로 진행함 → 그 시점에 `docs/stitch/`에 프롬프트·맥락 md를 만듦

T0.3 원본 파일 이관과 목록
- 10개 파일을 이름 그대로 `data/raw/`에 복사함 (Downloads의 다른 파일은 건드리지 않음)
- 복사본과 원본의 sha256이 같은지 확인함
- `manifest.csv` 열: `source_id, file_name, provider, portal_url, reference_date, sha256, bytes, rows, note`
  - source_id 예: `kisa_2025`, `kisa_2026`, `ftc_affiliates`, `ftc_groups`, `ngms_emission`, `kicox_factories`, `kicox_region_scale` 등
  - portal_url은 포털 대표 주소로 적음 (KISA 정보보호 공시 종합포털, 공정위 기업집단포털, NGMS, 공공데이터포털). 데이터셋 상세 주소는 확인되는 대로 채움
  - rows는 점검 때 확인한 행 수 (예: kisa_2026 826, ftc_affiliates 3,539, ngms_emission 772)
- 코드는 파일명을 직접 쓰지 않고 manifest의 source_id로 파일을 찾게 함 → 파일명 표기(공백·밑줄)가 달라도 manifest만 고치면 됨

T0.4 파이썬 환경
- Anaconda Python 3.11.7로 `.venv` 생성 (Anaconda 기본 환경과 섞이지 않게 함)
- `requirements.txt`(앱, Cloud 배포용): streamlit, pandas, pyarrow, seaborn, matplotlib
- `requirements-pipeline.txt`: `-r requirements.txt` + openpyxl(xlsx 읽기), requests, python-dotenv, pytest
- 설치 후 실제 버전으로 고정함. streamlit은 로컬과 같은 1.62.0을 기준으로 함. pandas가 3.x로 설치되면 원본 읽기 스모크 테스트를 돌려 보고 문제가 있으면 2.x로 고정함
- `.env.example`: `DART_API_KEY=` (값 없음)

T0.5 코드 골격과 테스트 실행 확인
- 전체 계획 3장 구조대로 빈 패키지(`__init__.py`)만 만듦. 기능 코드는 넣지 않음
- `data/manual/`, `data/processed/`에 `.gitkeep`
- `pytest.ini`: testpaths=tests, `live` 마커 등록 (실제 DART 호출 테스트용, 기본 실행에서 제외)
- `tests/test_raw_manifest.py`: manifest의 모든 파일이 `data/raw/`에 있고 sha256이 일치하는지 확인함. 원본이 없는 환경(CI, Actions)에서는 건너뜀

T0.6 GitHub 저장소 생성과 첫 푸시
- 실행 직전에 사용자에게 확인: 저장소 이름(제안 `mfg-it-radar`), 공개 여부(전체 계획은 공개 전제)
- 푸시 전 점검: `git ls-files`에 `data/raw/`의 원본 파일·`.env`·`.venv`가 없는지, 키로 보이는 문자열이 없는지 확인
- `gh repo create <이름> --public --source . --push`, 첫 커밋 메시지에 작업 내용 요약

T0.7 OpenDART 키 발급·보관 안내
- `docs/guides/dart-api-key.md`: OpenDART(opendart.fss.or.kr) 회원가입 → 인증키 신청 → 발급 확인 → 로컬 `.env`에 저장 → GitHub Secrets 등록 절차
- 키는 사용자가 직접 입력함. 대화창이나 문서, 커밋에 키 값을 적지 않음
  - 로컬: `.env` 파일에 `DART_API_KEY=발급받은값` 한 줄을 사용자가 직접 씀
  - GitHub: 사용자가 터미널에서 `gh secret set DART_API_KEY`를 실행하고 프롬프트에 값을 붙여 넣음
- 1인 1키라 유출되면 대체 키가 없다는 점을 적음

## 5. 완료 기준

| 기준 | 확인 방법 |
|---|---|
| 저장소와 무시 규칙이 동작함 | `git check-ignore data/raw/<원본파일>`이 무시로 나오고 `data/raw/manifest.csv`는 추적됨 |
| 문서가 제자리에 있음 | `docs/spec/SPEC.md`, `docs/data-schema.md`, `docs/plans/00-master-plan.md`, `docs/plans/M0-setup/phase-plan.md`, `CLAUDE.md` 존재 |
| 원본 10개 파일이 온전함 | `tests/test_raw_manifest.py` 통과 (sha256 일치) |
| 파이썬 환경이 동작함 | `.venv\Scripts\python -m pytest` 통과, streamlit·pandas·seaborn·openpyxl import 성공, 2026 KISA 파일을 읽어 826행 확인 |
| 원격 저장소에 올라감 | GitHub에 첫 커밋이 있고 원본 파일·`.env`가 올라가지 않음 |
| 사용자 작업이 시작됨 | OpenDART 키 신청 여부를 사용자에게 확인함 (발급 완료는 M3 전까지만 필요하고 M1 진행을 막지 않음) |

## 6. 위험과 대응

| 위험 | 대응 |
|---|---|
| 한글 파일명이 PowerShell에서 깨지거나 검색에서 빠짐 (기획 단계에서 실제로 발생) | 한글 경로 작업은 Git Bash·Python으로 함. 파일 확인은 sha256으로 함 |
| Anaconda 기본 환경과 `.venv`가 섞여 버전이 어긋남 | 명령마다 `.venv\Scripts\python`을 명시함 |
| 최신 pandas(3.x)의 기본 동작 변화로 원본 읽기가 달라짐 | 설치 직후 KISA 2026 파일을 읽어 행 수·열 형식을 확인하고, 문제가 있으면 2.x로 고정함 |
| 공개 저장소에 원본·개인정보·키가 올라감 | `.gitignore`, 푸시 전 `git ls-files` 점검, 키는 사용자가 직접 입력 |
| 산단공 공장 CSV(21MB)가 저장소를 키움 | 원본은 커밋하지 않고 manifest만 커밋함 |
| Downloads의 원본이 지워지거나 바뀜 | `data/raw/`로 복사하고 sha256을 기록해 두어 바뀌면 테스트가 알려 줌 |

## 7. 진행 기록

- 2026-09-28
  - 사용자 승인 (저장소 이름 `mfg-it-radar`, 공개)
  - T0.1 저장소 초기화 완료. 무시 규칙을 임시 파일로 확인함
  - T0.2 SPEC 사본(sha256 일치), `CLAUDE.md` 작성 완료
  - T0.3 원본 10개 복사(sha256 10/10 일치), `manifest.csv` 작성 완료. 행 수 6종이 점검값과 같음
  - T0.4 `.venv`와 패키지 고정 완료. pandas가 3.0.6으로 설치되어 기획 단계 결과와 대조함 → 모두 같아 3.0.6 유지
  - T0.5 코드 골격과 원본 무결성 테스트 완료 (정상 12 passed, 파일 누락 시 실패, 원본 없는 환경에서 건너뜀 확인)
  - T0.7을 T0.6보다 먼저 수행함 (키 안내 문서를 첫 커밋에 넣으려고 순서를 바꿈)
  - T0.6 푸시 전 점검 통과 → 첫 커밋 `9d2cdfc` → 공개 저장소 생성·푸시 완료. 원격에 원본 없음 확인
  - 단계 결과와 M1 연결 내용 기록, 두 번째 커밋으로 올림

## 8. 결과

| 완료 기준 | 판정 | 근거 |
|---|---|---|
| 저장소와 무시 규칙이 동작함 | 충족 | 원본·`.env`·캐시는 무시, `manifest.csv`는 추적 (T0.1) |
| 문서가 제자리에 있음 | 충족 | SPEC 사본(sha256 일치), 스키마, 전체 계획, M0 계획, `CLAUDE.md`, 작업 계획서 7개 |
| 원본 10개 파일이 온전함 | 충족 | 무결성 테스트 12 passed. 파일 누락 시 실패, 원본 없는 환경에서 건너뜀도 확인 (T0.5) |
| 파이썬 환경이 동작함 | 충족 | import 9종, `pip check` 이상 없음, pandas 3.0.6에서 KISA 2026 826행 (T0.4) |
| 원격 저장소에 올라감 | 충족 | https://github.com/eugeejo-ui/mfg-it-radar (공개), 원격에 원본·`.env` 없음 (T0.6) |
| 사용자 작업이 시작됨 | 남음 | OpenDART 키 신청은 사용자 작업. M3 전까지 필요하고 M1은 막지 않음 |

계획과 달라진 점
- T0.7을 T0.6보다 먼저 수행함 (안내 문서를 첫 커밋에 넣으려고)
- pandas 3.0.6이 설치되어 기획 단계(2.1.4) 결과와 대조함 → 행 수·결합 수가 모두 같아 3.0.6을 유지함
- 버전 고정 확인은 새 가상환경을 다시 만드는 대신, 같은 환경에서 재설치로 바뀌는 패키지가 없는지와 `pip check`로 확인함
- manifest에 `encoding` 열을 추가함 (계획에 없던 열. CSV 인코딩을 코드가 추측하지 않게 하려는 것)
- `CLAUDE.md`에 `PYTHONUTF8=1` 사용 규칙을 추가함 (Git Bash 콘솔에서 한글 출력이 깨지는 것을 T0.5에서 발견함)

## 9. 다음 단계로 이어지는 내용

### M1(원본 정제)에 넘기는 산출물

| 산출물 | M1에서 쓰는 방식 |
|---|---|
| `data/raw/` 원본 10개 + `manifest.csv` | 정제 코드가 source_id로 파일을 찾고 `encoding` 값을 그대로 씀. 파일명을 코드에 직접 쓰지 않음 |
| `.venv`, 고정된 requirements | `.venv\Scripts\python`으로 실행함. 새 패키지가 필요하면 `requirements-pipeline.txt`에 버전을 고정해 추가함 |
| 빈 패키지 골격 | `pipeline/sources/kisa.py` 등을 제자리에 추가함 |
| pytest 설정, 무결성 테스트 | M1 테스트를 `tests/`에 추가함. `live` 마커는 M3용 |
| 회귀 기준값 (pandas 3.0.6에서 재확인) | 정보보호 제조업 387, 증감 계산 351, 공정위 이름 일치 125, 배출권 142, 공장 334 → M1 회귀 테스트의 기대값 |
| `CLAUDE.md` 규칙 | 데이터 원칙(비노출, 값 없음/0 구분 등)을 정제 코드에 반영함 |

### M1의 선행 조건

- M1 단계 상세 계획서를 쓰고 사용자 승인을 받아야 함
- DART 키는 필요 없음 (M1은 파일만으로 진행함)

### M1으로 넘어간 할 일

- manifest 재생성을 재사용 가능한 명령으로 만듦 (M0에서는 세션 임시 폴더의 일회성 스크립트를 씀)
- CI(`ci.yml`)를 만듦. GitHub에서는 원본이 없어 무결성 테스트가 "2 passed, 10 skipped"로 나오는 것이 정상임. 푸시 전 점검(금지 경로, 키·법인등록번호 형태 문자열)의 자동화도 검토함
- 정제 코드 주의
  - pandas 3에서는 문자열 열 dtype이 `str`임
  - 공정위 소속회사는 `dtype=str`로 읽어 법인등록번호 앞자리를 보존함

### 남은 문제

| 항목 | 담당 | 기한 |
|---|---|---|
| OpenDART 키 신청·로컬 `.env` 저장 | 사용자 | M3 시작 전 |
| GitHub Secrets `DART_API_KEY` 등록 (`docs/guides/dart-api-key.md` 3장) | 사용자 | M5 시작 전 (Actions가 쓰기 전) |
| Streamlit Community Cloud 연결 | 사용자 | M2 배포 시점 |
| manifest의 데이터셋 상세 주소 채우기 | Claude | M2 출처 페이지 전 |
| 시도별 통계 4종 표 구조 재확인 | Claude | 이 자료를 쓰는 시점 |
| M3: 요청 URL을 로그로 남길 때 `crtfc_key`를 가림 | Claude | M3 DART 클라이언트 작성 시 |
