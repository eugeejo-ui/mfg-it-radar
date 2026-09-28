# OpenDART API 키 발급과 보관

이 서비스는 금융감독원 OpenDART API로 기업개황, 재무, 공시를 가져옴. 키는 사용자 본인이 발급받아 직접 넣음. 키 값은 이 문서, 코드, 커밋, 대화창 어디에도 적지 않음.

## 1. 발급

1. OpenDART 누리집(https://opendart.fss.or.kr)에 접속함
2. 인증키 신청 메뉴에서 약관에 동의하고 신청 정보를 입력함 (메뉴 이름은 사이트 개편에 따라 다를 수 있음)
3. 입력한 메일로 온 인증 절차를 마침
4. 인증키 관리 화면에서 발급된 키(40자리 영숫자)를 확인함

알아 둘 점
- 이용약관상 1인 1키 원칙임 (19조 5항). 유출되면 새 키를 받기 어려울 수 있으니 처음부터 아래 방법으로만 보관함
- 호출 한도는 약 2만 건이며 넘으면 020 오류가 남. 이 서비스는 초기 적재 약 1.4~1.8천 건, 매일 50~200건을 씀

## 2. 로컬 보관 (내 PC)

1. 프로젝트 폴더에서 `.env.example`을 복사해 `.env`를 만듦
2. `.env`를 메모장 등으로 열어 `DART_API_KEY=` 뒤에 발급받은 키를 붙여 넣고 저장함
3. `.env`는 `.gitignore`에 들어 있어 커밋되지 않음. 확인하려면 터미널에서 아래 명령을 실행함. `.env`가 출력되면 무시되고 있는 것임

```bash
git check-ignore .env
```

## 3. GitHub 보관 (자동 갱신용)

GitHub Actions가 매일·매월 DART를 호출하려면 저장소 비밀 값(Secrets)에 키가 있어야 함. 저장소 `mfg-it-radar`가 만들어진 뒤에 두 방법 중 하나로 등록함.

- 터미널: 아래 명령을 실행하고, 값을 묻는 프롬프트에 키를 붙여 넣음

```bash
gh secret set DART_API_KEY --repo eugeejo-ui/mfg-it-radar
```

- 웹: 저장소 Settings → Secrets and variables → Actions → New repository secret → 이름 `DART_API_KEY`, 값에 키 입력

등록된 비밀 값은 GitHub 화면에서도 다시 볼 수 없고, Actions 로그에서는 가려져 나옴.

## 4. 하지 말 것

- 대화창(Claude 포함)에 키를 붙여 넣지 않음
- 코드, 문서, 이슈, 커밋 메시지에 키를 쓰지 않음
- 키가 보이는 화면을 캡처해 공유하지 않음
- `gh secret set DART_API_KEY --body <키>`처럼 명령줄에 키를 직접 쓰지 않음 (셸 기록에 남음)

## 5. 동작 확인

- M3 첫 작업에서 로컬 `.env`의 키로 DART를 한 번 호출해 응답 상태 코드만 출력함. 키 값은 출력하지 않음
- 키가 유출됐다고 의심되면 바로 OpenDART 인증키 관리 화면에서 조치하고, GitHub Secrets 값도 바꿈
