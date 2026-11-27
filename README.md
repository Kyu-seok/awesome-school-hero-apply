# 히어로스쿨 교육 신청 시스템

학교·기관 담당자가 히어로스쿨 "인공지능 히어로" 교육을 보고 같은 페이지에서 수업을 신청하면, 어썸스쿨 운영자가 그 신청을 한곳에서 관리하는 서비스입니다. 흐름은 **교육 소개 → 신청 접수 → 신청 관리** 입니다.

- 신청자는 기관 정보, 수업 희망일, 연락 가능 날짜를 입력해 신청합니다. 접수 직후 **접수 확인 메일**을 받습니다.
- 연락 가능 날짜 아침, 신청이 아직 **접수됨** 상태이면 **연락일 안내 메일**이 자동으로 나갑니다.
- 운영자는 `/manage/`에서 "오늘 연락할 신청"을 먼저 보고, 필터·상태 변경·운영 메모를 쓰고, 신청 목록을 Google 시트로 내보냅니다.

용어는 [`GLOSSARY.md`](GLOSSARY.md)를 따릅니다. 전체 요구사항은 [스펙 이슈 #1](https://github.com/Kyu-seok/awesome-school-hero-apply/issues/1)에 있습니다.

## 바로 확인하기

| 항목 | 위치 |
| --- | --- |
| 배포된 서비스 | https://hero-school.kyuships.com |
| API 문서(Swagger UI) | https://hero-school.kyuships.com/api/docs/ |
| 관리자 페이지 | https://hero-school.kyuships.com/manage/ |
| 내보내기 결과 시트(보기 전용) | https://docs.google.com/spreadsheets/d/1-BW3k_Vkk8a4Z-1r7yZqFqonEMZ4majOxTNOo-N-g5c/edit |

**데모 운영자 계정**: 아이디 `demo-operator`, 비밀번호 `hero-demo-2026`

- 심사용으로 공개한 계정입니다. 운영자 권한(`is_staff`)만 있고 Django admin(`/admin/`)에는 들어갈 수 없습니다.
- 데모 신청 12건이 들어 있습니다. 관리자 페이지의 "내보내기"를 누르면 위 시트가 현재 전체 신청 목록으로 덮어써집니다.
- 배포된 서비스에서 신청하면 입력한 이메일로 실제 메일이 나갑니다. 받을 수 있는 주소로만 신청해 주세요.

## 로컬에서 실행하기

필요한 것: Docker(Compose v2). Python이나 Node를 따로 설치하지 않아도 됩니다.

```sh
git clone https://github.com/Kyu-seok/awesome-school-hero-apply.git
cd awesome-school-hero-apply
docker compose up -d --build
```

`web` 컨테이너가 시작하면서 마이그레이션을 적용합니다. 아래 명령이 `200`을 출력하면 준비된 것입니다(첫 빌드는 몇 분 걸립니다).

```sh
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/
```

데모 운영자 계정과 데모 신청을 넣습니다. 여러 번 실행해도 결과가 같습니다.

```sh
docker compose exec web python manage.py seed_demo
```

이제 다음 주소를 열 수 있습니다.

- 교육 소개와 신청 폼: http://localhost:8000/
- 관리자 페이지: http://localhost:8000/manage/ (`demo-operator` / `hero-demo-2026`)
- API 문서: http://localhost:8000/api/docs/

로컬 구성에서 달라지는 점:

- 메일은 실제로 보내지 않고 `worker` 로그에 찍습니다: `docker compose logs -f worker`
- 시트 내보내기는 메모리 어댑터로 돌아서 실제 시트에 쓰지 않습니다. 실제 시트로 보내려면 `scripts/setup-google-sheets.sh`를 따라 설정합니다.
- Django admin을 쓰려면 superuser를 만듭니다: `docker compose exec web python manage.py createsuperuser`

정리: `docker compose down -v` (`-v`는 DB 볼륨까지 지웁니다)

### 테스트

Python 3.12, [uv](https://docs.astral.sh/uv/), PostgreSQL이 있으면 컨테이너 없이 테스트를 돌릴 수 있습니다. DB는 `DATABASE_URL`로 지정합니다(없으면 로컬 유닉스 소켓의 `hero_school`).

```sh
uv sync
uv run ruff check . && uv run pytest
```

CI(GitHub Actions)는 PostgreSQL 16 서비스 컨테이너를 띄우고 같은 명령을 실행합니다.

## 사용 기술

| 영역 | 기술 |
| --- | --- |
| 백엔드 | Python 3.12, Django 5.2 LTS, Django REST framework, drf-spectacular |
| 비동기 작업 | Celery 5(worker, beat), Redis 7 |
| DB | PostgreSQL 16 |
| 화면 | Django 템플릿, SCSS(Docker 빌드 단계에서 컴파일), vanilla JS, Pretendard |
| 외부 연동 | Gmail SMTP(메일), Google Sheets API(서비스 계정) |
| 개발 도구 | uv, ruff, pytest-django, time-machine, GitHub Actions |
| 배포 | Docker Compose(nginx, gunicorn, postgres, redis, worker, beat), Cloudflare Tunnel |

## 설계 의도

### 신청을 기관(B2B) 단위 요청으로 모델링했습니다

과제 문구 "교육 신청"만 보면 학생이나 보호자가 기수에 등록하는 B2C 흐름으로도 읽힙니다. 실제 히어로스쿨 사이트를 조사해 보니, 학교·기관 담당자가 교육과 수업 희망일을 골라 문의하고 담당자가 연락해 일정을 확정하는 B2B 흐름이었습니다. 그래서 신청은 "한 기관이 하나의 교육을 특정 수업 희망일에 받고 싶다는 요청"으로 두고, 기수·정원 개념은 넣지 않았습니다. "수업 희망일은 신청일로부터 최소 3주 뒤" 같은 실제 운영 규칙을 도메인 규칙으로 옮겼습니다.

근거와 검토한 대안: [ADR 0001](docs/adr/0001-model-applications-as-b2b-org-requests.md)

### "연락 가능 날짜 기준 자동 안내 메일"의 해석

과제 문구가 모호해서 해석이 필요했습니다. 실제 서비스의 "신청 후 담당자 연락" 흐름에 맞춰, **운영자가 전화하기 전에 메일로 먼저 연락을 열어 주는 자동화**로 해석했습니다.

- 신청자는 연락 가능 날짜를 평일 중에서 고릅니다. 내일 이후이고 수업 희망일보다 앞서야 합니다. 공휴일은 따지지 않습니다.
- 연락 가능 날짜 당일 09:00(KST)부터 17:00까지 매시 정각에 Celery beat가 발송 작업을 실행합니다. 대상은 연락 가능 날짜가 오늘이고, **접수됨** 상태이고, 아직 안내 메일을 보내지 않은 신청입니다.
- 운영자가 그 전에 이미 연락해서 **연락 완료**로 바꿨거나 신청이 취소되었다면 보내지 않습니다.
- 신청마다 행을 잠그고 발송 시각을 기록해 중복 발송을 막습니다. 한 건이 실패해도 나머지는 계속 보내고, 실패한 건은 그날 안에서만 다음 정각에 다시 보냅니다. 다음 날에는 보내지 않습니다.

### 규칙은 서비스 레이어 한곳에 둡니다

날짜 규칙, 중복 규칙, 상태 변경은 serializer나 view가 아니라 `applications/services.py`가 가집니다. 공개 API, 운영자 API, 관리자 페이지가 같은 함수를 부르므로 규칙이 한곳에만 있습니다. 바깥에 드러나는 진입점은 셋입니다.

- `receive_application`: 검증, 중복 확인, 저장, 접수 확인 메일 예약(커밋 뒤 `on_commit`으로 Celery에 넣음)
- `change_status`: 상태와 운영 메모 변경
- `send_todays_contact_day_emails`: 오늘의 연락일 안내 발송

중복 신청은 서비스에서 먼저 확인해 "이미 접수된 신청이 있습니다"를 돌려주고, DB에도 부분 유니크 제약(이메일 소문자 + 교육 + 수업 희망일, 취소 제외)을 걸어 동시 요청까지 막습니다. 취소된 신청 뒤에는 같은 조건으로 다시 신청할 수 있습니다.

시트 내보내기는 "행 목록으로 시트 덮어쓰기"라는 인터페이스 하나 뒤에 Google Sheets 어댑터와 메모리 어댑터를 두고, 설정(`EXPORTS_SHEET_BACKEND`)으로 고릅니다.

### 테스트는 바깥에서 관찰할 수 있는 동작만 봅니다

모델 메서드나 serializer를 직접 테스트하지 않고, 세 개의 seam에서 HTTP 응답, DB 상태, 발송된 메일, 시트에 쓰인 행을 확인합니다.

1. **HTTP 경계**(메인): DRF `APIClient`와 Django `Client`로 실제 URL을 호출합니다. 교육 조회, 신청 접수의 모든 검증 규칙(3주, 평일, 날짜 범위, 동의, 중복, 취소 후 재신청, honeypot), 접수 확인 메일, 운영자 권한(익명·일반 사용자·운영자), 상태 변경과 메모.
2. **오늘의 연락일 안내 발송 진입점**: `time-machine`으로 날짜·시각을 고정하고 직접 호출합니다. 대상 선별, 두 번 실행해도 한 번만 발송, 한 건 실패가 나머지를 막지 않음, 같은 날 재시도.
3. **시트 어댑터**: 메모리 어댑터로 바꿔 끼우고 관리자 페이지에서 내보내기를 실행해, 헤더와 전체 신청이 정해진 열 순서로 덮어써지는지 확인합니다.

실제 Gmail, Google API, nginx, Cloudflare는 자동 테스트하지 않고 배포 뒤 손으로 확인했습니다.

### 스팸 방지

신청 폼에 숨김 honeypot 필드(`website`)를 두고, 값이 들어오면 저장하지 않으면서 성공처럼 응답합니다. 신청 접수 API에는 IP 기준 익명 throttle(기본 시간당 10건)을 걸었고, 배포에서는 throttle 기록을 Redis에 두어 gunicorn 프로세스 여러 개가 같은 기록을 봅니다.

## API 요약

전체 명세와 직접 호출은 [`/api/docs/`](https://hero-school.kyuships.com/api/docs/)에서 할 수 있습니다(OpenAPI 스키마: `/api/schema/`).

| 메서드와 경로 | 권한 | 설명 |
| --- | --- | --- |
| `GET /api/programs/` | 누구나 | 공개된 교육 목록 |
| `GET /api/programs/{slug}/` | 누구나 | 교육 상세와 교시별 커리큘럼. 공개되지 않은 교육은 404 |
| `POST /api/applications/` | 누구나(throttle) | 신청 접수. 성공하면 201과 신청 ID·상태·연락 가능 날짜. 검증 실패와 중복은 400과 필드별 오류 |
| `GET /api/applications/` | 운영자(세션) | 신청 목록. 상태·교육·연락 가능 날짜 필터, 페이지네이션 |
| `PATCH /api/applications/{id}/` | 운영자(세션) | 상태와 운영 메모만 변경 |

운영자 전용 API에 권한이 없으면 403을 돌려줍니다.

## 저장소 구성

| 경로 | 내용 |
| --- | --- |
| `programs/` | 교육과 커리큘럼 모델, 공개 API, 랜딩 페이지 |
| `applications/` | 신청 모델, 도메인 규칙(서비스 레이어), 신청 API와 운영자 API |
| `notifications/` | 접수 확인 메일과 연락일 안내 메일(템플릿, Celery 작업) |
| `backoffice/` | 관리자 페이지 `/manage/`, `seed_demo` 명령 |
| `exports/` | Google Sheets 내보내기(어댑터, Celery 작업, 마지막 내보내기 기록) |
| `config/` | 설정(모든 환경값은 환경변수), URL, Celery 앱 |
| `styles/`, `static/` | SCSS 원본, 대표 이미지(직접 그린 SVG), JS |
| `tests/` | 테스트(기능 영역별 파일) |
| `compose.yaml` | 로컬 개발 구성 |
| `compose.prod.yaml`, `deploy/`, `deploy.sh` | 배포 구성과 배포 스크립트 |

## 배포

미니 PC에서 Docker Compose 프로젝트로 돌고, Cloudflare Tunnel이 `hero-school.kyuships.com`을 nginx(`127.0.0.1:8120`)로 연결합니다. nginx만 호스트 포트를 열고, 나머지(gunicorn+Django, postgres, redis, worker, beat)는 compose 네트워크 안에만 있습니다.

- 배포: 미니 PC에서 `./deploy.sh` (git pull → build → migrate → collectstatic → up). 미니 PC가 내부망에 있어서 CI 자동 배포는 하지 않습니다.
- 비밀 정보(`DJANGO_SECRET_KEY`, DB 비밀번호, Gmail 앱 비밀번호, 서비스 계정 키)는 미니 PC의 `.env`와 저장소 밖 키 파일에만 있습니다. 저장소에는 [`.env.example`](.env.example)만 있습니다.
- AWS로 옮긴다면: [AWS 배포 계획](docs/aws-deployment.md)

## 문서

- [`GLOSSARY.md`](GLOSSARY.md): 용어집
- [`docs/adr/0001-model-applications-as-b2b-org-requests.md`](docs/adr/0001-model-applications-as-b2b-org-requests.md): 신청을 B2B 요청으로 모델링한 결정
- [`docs/aws-deployment.md`](docs/aws-deployment.md): AWS 배포 계획(2단계, 넘어가는 기준과 대략적인 비용)
- [`docs/ai-usage.md`](docs/ai-usage.md): AI(Claude Code) 활용 내역, 사람이 결정한 것과 AI가 한 것

## 알려진 한계

- **교육 소개 문구와 커리큘럼은 임시 콘텐츠입니다.** 실제 "인공지능 히어로" 교육의 6교시 구성을 참고해 데모용으로 쓴 글이고, 원문을 확인하지 못해 출처 표기를 아직 하지 않았습니다. 원문을 확인하면 데이터 마이그레이션으로 고치고 출처를 적을 계획입니다. 대표 이미지는 직접 그린 SVG입니다.
- **개인정보 수집·이용 안내 문구도 데모용 임시 문구입니다.** 항목, 목적, 보유 기간의 구조는 갖췄지만 법무 검토를 거친 문구가 아닙니다.
- 연락일 안내 메일은 "최소 한 번" 발송을 보장합니다. 메일 서버에 넘긴 뒤 발송 시각 기록이 커밋되기 전에 실패하면 같은 날 한 번 더 갈 수 있습니다. 놓치는 쪽보다 낫다고 판단했습니다.
- 공휴일은 따지지 않습니다. 연락 가능 날짜는 평일 여부만 봅니다.
