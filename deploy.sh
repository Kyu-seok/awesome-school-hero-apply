#!/usr/bin/env bash
# 프로덕션 배포: git pull → build → migrate → collectstatic → up -d.
# 몇 번을 다시 실행해도 결과가 같다(마이그레이션과 collectstatic은 이미 반영된 것을 건너뛴다).
#
#   ./deploy.sh            # 미니 PC에서
#   ./deploy.sh --no-pull  # 지금 체크아웃된 코드 그대로 배포
#
# 데모 데이터(데모 운영자 계정, 데모 신청)는 자동으로 넣지 않는다. 필요할 때 한 번 실행한다:
#   docker compose -f compose.prod.yaml exec web python manage.py seed_demo
# Django admin용 superuser도 같은 방식으로 만든다(manage.py createsuperuser).
set -euo pipefail

cd "$(dirname "$0")"

pull=1
for arg in "$@"; do
  case "$arg" in
    --no-pull) pull=0 ;;
    *) echo "알 수 없는 옵션: $arg" >&2; exit 2 ;;
  esac
done

if [[ ! -f .env ]]; then
  echo ".env가 없습니다. .env.example을 복사해 채운 뒤 다시 실행하세요." >&2
  exit 1
fi

compose() { docker compose -f compose.prod.yaml "$@"; }

if (( pull )); then
  echo "==> git pull"
  git pull --ff-only
fi

echo "==> build"
compose build

echo "==> migrate"
compose up -d --wait db
compose run --rm --no-deps web python manage.py migrate --noinput

echo "==> collectstatic"
compose run --rm --no-deps web python manage.py collectstatic --noinput

echo "==> up"
compose up -d --remove-orphans --wait

compose ps
