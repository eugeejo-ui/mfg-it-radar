# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트

- 제조업 IT 투자 레이더(가칭): 정보보호 공시를 낸 제조사 387곳의 IT·보안 투자, 구매 경로(계열 SI), 탄소 규제, 공장 거점, 최근 DART 공시를 모아 보여주는 비영리 공개 Streamlit 서비스임. 주 사용자는 IT 솔루션 발굴 영업임
- 저장소: https://github.com/eugeejo-ui/mfg-it-radar (공개)
- 현재 단계는 `docs/plans/M*/phase-plan.md` 맨 위 `- 상태:` 줄로 확인함 (M0 완료, 다음 M1 원본 정제)
- 문서 체계는 `docs/README.md`, 결정과 마일스톤은 `docs/plans/00-master-plan.md`

## 명령

Git Bash 기준. 파이썬은 항상 프로젝트 가상환경을 씀 (Anaconda 기본 환경을 쓰지 않음).

```bash
.venv/Scripts/python -m pytest                                    # 전체 테스트 (live 제외)
.venv/Scripts/python -m pytest tests/test_raw_manifest.py::test_manifest_source_ids_are_unique  # 테스트 하나
.venv/Scripts/python -m pytest -k kisa_2026                       # 이름으로 골라 실행
.venv/Scripts/python -m pytest -m live                            # 실제 DART 호출 테스트 (수동 전용, M3부터)
.venv/Scripts/python -m pip install -r requirements-pipeline.txt  # 환경 재구성
```

- 한글 출력이 깨지면 명령 앞에 `PYTHONUTF8=1`을 붙임
- `requirements.txt`는 앱(Streamlit Cloud 배포)용, `requirements-pipeline.txt`는 정제·수집·테스트용임. 둘 다 `==`로 버전을 고정함
- 원본 무결성 테스트는 원본이 없는 환경(CI·Actions)에서 파일 검사를 건너뜀. 그곳에서는 "2 passed, 10 skipped"가 정상임
- 앱 실행과 파이프라인 실행 명령은 해당 단계(M1, M2)에서 만들고 여기에 추가함

## 구조

코드는 아직 빈 골격임(M0). 아래는 전체 계획 2~5장의 목표 구조로, 여러 파일에 걸친 흐름이라 먼저 알아 둘 것.

- 데이터 흐름: 원본 파일(연 1회, 관리자 PC) → `pipeline` 연간 빌드(정제 → 결합 → 검수) → `data/processed/*.parquet` 커밋 → Streamlit 앱은 parquet만 읽음. 앱은 런타임에 DART를 부르지 않고 키도 갖지 않음
- 자동 갱신: GitHub Actions가 매일 DART 공시, 매월 기업개황·재무를 받아 parquet을 커밋함 → Cloud에 자동 반영. Actions는 원본 파일 없이 processed 테이블과 대응표만으로 동작함
- 회사 기본키는 DART corp_code임
  - 공정위는 법인등록번호 = DART jurir_no로 정확 결합
  - KISA·배출권·공장은 이름 정규화로 결합 → 대응표(xwalk)와 사람 검수를 거침
  - `data/manual/xwalk_overrides.csv`가 자동 결과보다 항상 우선함
- 원본은 `data/raw/manifest.csv`의 source_id로 찾음. 파일명을 코드에 쓰지 않고, CSV 인코딩도 manifest 값을 씀
- 패키지 역할
  - `pipeline/sources`: 원본별 정제
  - `pipeline/dart`: API 클라이언트
  - `pipeline/jobs`: annual·daily·monthly
  - `app/pages`: 후보 목록·기업 브리프·데이터 출처
  - `app/blocks`: 브리프 블록별 1파일
- 결합 경로와 테이블 설계: `docs/data-schema.md`

## 원본 데이터

엑셀 5개는 형식 함정이 있어 아래 방법으로 읽어야 함. 열 구성·품질 문제·읽는 코드는 `docs/data-sources.md`에 있음.

| source_id | 파일 (`data/raw/`) | 행 | 키 | 읽을 때 |
|---|---|---|---|---|
| kisa_2025, kisa_2026 | `2025_정보보호_공시_이행_기업리스트.xlsx`, `2026_…` | 773, 826 | 없음 (기업명) | 금액 원 단위, 여부 `O`/`X`, 총임직원 소수가 다수(반올림), 업종 `제조업(10~34)` 형태, 투자항목 "첨부 참조" 행 구분 |
| ftc_affiliates | `소속회사 개요.xlsx` | 3,539 (3,521개사) | 법인등록번호 | `dtype=str`로 읽음. 금액은 쉼표 문자열·백만원·개별 기준. 매출 `"0"`은 값 없음. 18개사가 두 집단 소속(다대다). `구분`은 상장 여부가 아님(기업공개일로 판단). 업종코드 `C2011` 형식 |
| ftc_groups | `기업집단별 개요.xlsx` | 102 | 기업집단명 | 금액 쉼표 문자열(백만원). 상장·비상장 소속회사수 열은 전부 0 |
| ngms_emission | `배출권거래제 할당대상업체 현황_260101기준.xlsx` | 772 | 없음 (업체명) | `header=0, skiprows=[1]` 후 첫 열 제거. KSIC가 숫자형이라 `zfill(5)` |

- 산단공 CSV 5개는 cp949임. 등록공장 파일은 동명 회사가 섞여 있음 (결합 규칙은 data-schema)
- 회사명 정규화: SPEC 7장 정규식 + 영문 대문자화
- M1 회귀 기준값(pandas 3.0.6에서 확인)
  - 정보보호 제조업 387, 2개년 증감 계산 351
  - 이름 일치: 공정위 125, 배출권 142, 공장 334

## 진행 문서 규칙 (반드시 따름)

- 단계를 시작하기 전에 `phase-plan.md`를 쓰고 사용자 승인을 받음
- 작업을 수행하기 전에 `tasks/T<n>.<m>-<이름>.md`를 먼저 씀
- 단계나 작업을 마치면 해당 문서에 진행 기록, 결과(완료 기준 대비), 다음 단계로 이어지는 내용(넘기는 산출물, 남은 문제, 선행 조건)을 덧붙임
- 양식은 `docs/plans/_templates/`에 있음. 이름 규칙과 흐름은 `docs/README.md`
- 전체 계획이 바뀌면 `00-master-plan.md` 11장 변경 이력에 남김. `docs/spec/SPEC.md`는 원문이라 고치지 않음
- 원본을 새로 받으면 `docs/data-sources.md`의 수치·형식을 다시 확인해 고침
- 문서는 개조식 어미(~함, ~임)로 쓰고, 확인한 수치만 적음

## 데이터·화면 원칙

- 대표자·법인등록번호·사업자등록번호는 화면, processed 파일, 저장소에 두지 않음. 법인등록번호는 연간 로컬 빌드의 결합 확인에만 쓰고 캐시는 `data/cache/`(gitignore)에만 둠
- 재무는 `fs_div`로 연결·개별을 구분하고 한 비율 계산에 섞지 않음. IT 투자/매출에는 개별 매출만 씀
- 값 없음과 0을 구분함. KISA "첨부 참조"는 "공시 원문 참조"로 표시함
- 적합도 점수·순위를 만들지 않고, 비교 대상 수(N)를 항상 표시함. 벤치마크는 세부업종 × 규모 구간에서 시작해 10곳 미만이면 조건을 넓힘
- 모든 화면 블록에 출처와 기준일을 표기함. 화면 문구는 사용자 언어로 씀 (예: "정보기술부문 투자액(A)" → "IT 투자액")
- 그래프는 seaborn으로 그림

## 작업 주의

- 한글 경로·파일명은 Git Bash나 Python으로 다룸. PowerShell 5.1에서 한글 패턴이 파일 검색에서 빠진 사례가 있음
- DART 키는 사용자만 입력함. 키 값을 출력·기록하지 않고, 요청 URL을 로그로 남길 때 `crtfc_key`를 가림. 보관 위치는 로컬 `.env`와 GitHub Secrets `DART_API_KEY`뿐임 (`docs/guides/dart-api-key.md`)
- 공개 저장소임. `git add` 후 푸시 전에 아래 두 가지를 확인함 (`git grep`은 git에 등록된 파일만 검사하므로 `git add`를 먼저 함)
  - `git ls-files`에 `data/raw/`의 원본, `.env`, `.venv/`, `data/cache/`가 없음
  - `git grep -nE '\b[A-Za-z0-9]{40}\b|(^|[^0-9])[0-9]{13}([^0-9]|$)' -- ':!data/raw/manifest.csv'` 결과가 없음 (키·법인등록번호 형태)
- pandas 3에서는 문자열 열 dtype이 `str`임. `object`로 가정하지 않음

## 화면 (M2)

- 화면 디자인은 사용자가 Stitch로 진행함
- M2를 시작할 때 `docs/stitch/`에 두 파일을 만들어 넘김
  - Stitch에 바로 붙여 넣을 프롬프트
  - 맥락 md: 그때까지의 진행 상황, 결정, 화면 요구사항, 실제 데이터 예시, 디자인 방향, Streamlit 제약
- 확정된 디자인은 받아서 `.streamlit/config.toml` 테마와 최소한의 CSS로 Streamlit에 구현함
