# AWS 배포 계획

지금은 미니 PC 한 대에서 Docker Compose로 돌린다(nginx, gunicorn+Django, postgres, redis, celery worker, celery beat). 이 문서는 실제 서비스로 키울 때 AWS로 옮기는 계획이다. 실제 AWS 배포는 과제 범위 밖이라 계획만 적는다.

한 번에 옮기지 않고 두 단계로 나눈다. 각 단계는 "지금 구성으로는 감당이 안 되는 이유"가 생겼을 때만 넘어간다.

## 0단계: 지금(미니 PC)

- 구성: `compose.prod.yaml` 한 벌, Cloudflare Tunnel → nginx(`127.0.0.1:8120`)
- 비용: 전기료와 도메인 외에 거의 없다.
- 한계
  - 가정용 전원과 인터넷에 묶여 있다. 정전이나 회선 장애가 곧 서비스 장애다.
  - DB 백업, 모니터링, 장애 알림이 없다.
  - Gmail SMTP는 개인 계정 발송 한도(하루 수백 통)와 스팸 판정 위험이 있다.
  - 개인정보(신청자 연락처)를 개인 장비에 보관한다.

## 1단계: EC2 + Compose, 관리형 데이터 서비스

애플리케이션은 지금처럼 Compose로 띄우고, 잃으면 안 되는 상태(DB, 메일 발송, 파일)만 관리형 서비스로 옮긴다. 코드는 거의 바꾸지 않는다. 모든 연결 정보가 이미 환경변수이기 때문이다.

| 구성 요소 | 지금 | 1단계 |
| --- | --- | --- |
| 앱(nginx, web, worker, beat) | 미니 PC Compose | EC2 한 대에서 같은 Compose |
| DB | postgres 컨테이너 | RDS for PostgreSQL 16 |
| 브로커·캐시 | redis 컨테이너 | ElastiCache for Redis(브로커 DB 0, 캐시 DB 1) |
| 메일 | Gmail SMTP | SES(SMTP 인터페이스) |
| 업로드 파일·백업 | Docker 볼륨 | S3 |
| 외부 연결 | Cloudflare Tunnel | 그대로(EC2에서 cloudflared 실행, 인바운드 포트 없음) |

바꿀 것:

- `compose.prod.yaml`에서 `db`, `redis` 서비스를 빼는 override 파일을 두고, `DATABASE_URL`, `CELERY_BROKER_URL`, `CACHE_URL`을 RDS·ElastiCache 주소로 준다. 지금은 compose 파일이 이 셋을 컨테이너 주소로 고정하므로 이 부분만 손본다.
- SES는 Django SMTP 백엔드 그대로 `EMAIL_HOST=email-smtp.ap-northeast-2.amazonaws.com`과 SES SMTP 자격 증명으로 바꾼다. 발신 도메인 인증(DKIM)과 샌드박스 해제 요청이 먼저 필요하다.
- 대표 이미지 같은 업로드 파일은 django-storages로 S3에 둔다. RDS 자동 백업(7일)에 더해 주기적인 `pg_dump`를 S3에 보관한다.
- EC2·RDS·ElastiCache는 같은 VPC에 두고, RDS·ElastiCache 보안 그룹은 EC2 보안 그룹에서 오는 연결만 받는다.
- 배포는 지금처럼 `deploy.sh`를 EC2에서 실행한다(SSM Session Manager로 접속).

**넘어가는 기준(0단계 → 1단계)**: 아래 중 하나라도 해당하면 옮긴다.

- 실제 신청을 받기 시작해 장애가 곧 신청 유실이 된다.
- 신청자 개인정보를 회사가 관리하는 인프라에 두어야 한다.
- 메일 발송량이 Gmail 개인 계정 한도에 가까워지거나, 자체 도메인으로 메일을 보내야 한다.

**대략적인 월 비용: 약 60~70달러**

| 항목 | 가정 | 월 비용(USD) |
| --- | --- | --- |
| EC2 | t3.small 1대(2 vCPU, 2GiB), 온디맨드 | 약 19 |
| EBS | gp3 30GB | 약 3 |
| 퍼블릭 IPv4 | 1개 | 약 4 |
| RDS | db.t4g.micro, 단일 AZ, gp3 20GB, 백업 7일 | 약 20 |
| ElastiCache | cache.t4g.micro 1노드 | 약 18 |
| SES | 월 수천 통(1,000통당 0.1달러) | 1 미만 |
| S3 | 수 GB(파일과 백업) | 1 미만 |
| CloudWatch, 데이터 전송 | 소량 | 약 3 |

## 2단계: ECS Fargate, ALB, CloudFront, Secrets Manager

서버 한 대를 없애고 프로세스 종류별로 따로 띄워 따로 늘린다. 배포를 이미지 교체로 바꿔 무중단·롤백을 얻는다.

| 구성 요소 | 1단계 | 2단계 |
| --- | --- | --- |
| web | EC2의 gunicorn 컨테이너 | ECS Fargate 서비스(2개 이상, 여러 AZ), ALB 뒤 |
| worker | EC2의 컨테이너 | ECS Fargate 서비스(1개 이상, 큐 길이로 확장) |
| beat | EC2의 컨테이너 | ECS Fargate 서비스, 정확히 1개 |
| nginx | EC2의 컨테이너 | 없앰. TLS는 ALB(ACM 인증서), 정적 파일은 S3 + CloudFront |
| 마이그레이션 | `deploy.sh` | 배포 파이프라인에서 일회성 ECS 작업(`migrate`)으로 실행한 뒤 서비스 교체 |
| 비밀 정보 | EC2의 `.env`, 키 파일 | Secrets Manager → 작업 정의의 환경변수로 주입 |
| 이미지 | EC2에서 빌드 | GitHub Actions에서 빌드해 ECR에 푸시(OIDC로 AWS 인증) |
| DB | RDS 단일 AZ | RDS Multi-AZ |

바꿀 것:

- beat는 꼭 하나만 돌아야 한다. 두 개가 뜨면 연락일 안내 발송 작업이 두 번 들어간다(서비스 레이어가 행 잠금으로 중복 메일은 막지만, 의도한 구성이 아니다). ECS 서비스의 원하는 개수를 1로, 최대 비율을 100%로 두어 배포 중에도 겹치지 않게 한다.
- `collectstatic` 결과를 S3에 올리고 CloudFront로 서빙한다. CloudFront는 ALB 앞에도 두어 `/static/`은 S3로, 나머지는 ALB로 보낸다.
- 지금은 nginx가 Cloudflare의 `CF-Connecting-IP`를 `X-Forwarded-For`로 넘겨 신청 접수 throttle이 실제 클라이언트 IP를 센다. CloudFront → ALB 경로에서는 `X-Forwarded-For`에 프록시 두 단계가 붙으므로, DRF의 `NUM_PROXIES`를 맞춰 실제 IP를 읽게 한다.
- Google 서비스 계정 키 JSON도 Secrets Manager에 두고, worker 작업이 시작할 때 파일로 쓰거나 환경변수에서 읽도록 바꾼다.
- Fargate 작업은 프라이빗 서브넷에 두고, 외부 호출(SES, Google API)은 NAT 게이트웨이로 나간다.

**넘어가는 기준(1단계 → 2단계)**: 아래 중 하나라도 해당하면 옮긴다.

- 학기 초처럼 신청이 몰리는 시기에 EC2 한 대의 CPU·메모리가 지속적으로 70%를 넘는다.
- web과 worker의 부하가 따로 움직여서(예: 내보내기·메일 작업이 쌓이는데 웹은 한가함) 따로 늘려야 한다.
- 배포 중 수십 초의 중단도 받아들일 수 없거나, 잘못된 배포를 이미지 단위로 바로 되돌려야 한다.
- 여러 사람이 배포하게 되어 서버에 접속해 스크립트를 돌리는 방식이 위험해진다.
- 서버 한 대의 장애나 AZ 장애에도 서비스가 살아 있어야 한다.

**대략적인 월 비용: 약 200달러 안팎**

| 항목 | 가정 | 월 비용(USD) |
| --- | --- | --- |
| Fargate web | 0.5 vCPU / 1GB × 2개 | 약 42 |
| Fargate worker | 0.5 vCPU / 1GB × 1개 | 약 21 |
| Fargate beat | 0.25 vCPU / 0.5GB × 1개 | 약 10 |
| ALB | 1개, 적은 트래픽 | 약 22 |
| NAT 게이트웨이 | 1개(단일 AZ), 적은 전송량 | 약 45 |
| RDS | db.t4g.micro Multi-AZ, gp3 20GB | 약 40 |
| ElastiCache | cache.t4g.micro 1노드 | 약 18 |
| CloudFront, S3 | 적은 트래픽 | 약 3 |
| Secrets Manager | 비밀 5개 | 약 2 |
| ECR, CloudWatch Logs, SES | 소량 | 약 5 |

NAT 게이트웨이가 큰 비중을 차지한다. 비용을 줄이려면 Fargate 작업을 퍼블릭 서브넷에 퍼블릭 IP로 두거나(보안 그룹으로 인바운드 차단), S3·ECR·Secrets Manager는 VPC 엔드포인트로 연결하는 방법을 검토한다.

## 비용 산정 가정

- 리전은 서울(`ap-northeast-2`), 온디맨드 요금, 한 달 730시간, 달러 기준이다. 세금과 지원 플랜은 뺐다.
- 트래픽은 교육 신청 서비스 규모(하루 신청 수십 건, 메일 수백 통, 페이지뷰 수천)로 가정했다. 데이터 전송 요금은 이 규모에서 몇 달러 수준이다.
- 프리 티어와 Savings Plans·예약 인스턴스 할인은 넣지 않았다. 1년 약정이면 EC2·RDS·ElastiCache 비용이 대략 30~40% 줄어든다.
- 단가는 공개 요금 수준으로 어림한 값이고 정확한 견적이 아니다. 실제 도입 전에는 AWS Pricing Calculator로 다시 계산한다.
