# 제조업 IT 투자 레이더 (가칭)

정보보호 공시를 낸 제조사 387곳의 IT·보안 투자, 구매 경로(계열 SI), 탄소 규제 노출, 공장 거점, 최근 DART 공시를 한 화면에 모아 보여주는 비영리 공개 서비스입니다. IT 솔루션 영업 담당자가 다음에 찾아갈 제조사를 고를 때 씁니다. 점수나 순위는 매기지 않고 신호만 보여줍니다.

## 문서

- 문서 체계 (어떤 문서가 어디에 있는지): [docs/README.md](docs/README.md)
- 서비스 명세: [docs/spec/SPEC.md](docs/spec/SPEC.md)
- 전체 계획: [docs/plans/00-master-plan.md](docs/plans/00-master-plan.md)
- 원본 데이터 참조: [docs/data-sources.md](docs/data-sources.md)
- 데이터 결합 스키마: [docs/data-schema.md](docs/data-schema.md)
- 단계·작업별 계획과 결과: [docs/plans/](docs/plans/)

## 현재 단계

- M1 원본 정제 완료 (2026-09-28): `python -m pipeline.jobs.annual`로 원본에서 정제 결과(`data/processed/`)까지 만듦. 다음 단계: M2 화면 (Stitch 핸드오프)

## 데이터 출처

KISA 정보보호 공시 종합포털, 공정거래위원회 기업집단포털, 국가온실가스종합관리시스템(NGMS), 한국산업단지공단(공공데이터포털), 금융감독원 DART OpenAPI. 원본 파일은 저장소에 올리지 않고 `data/raw/manifest.csv`에 출처·기준일·지문만 기록합니다.
