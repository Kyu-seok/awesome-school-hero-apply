# SCSS 빌드 단계: styles/*.scss를 static/css/site.css로 컴파일한다. 결과물은 커밋하지 않는다.
FROM node:22-slim AS styles
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY styles ./styles
RUN npm run build:css

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
COPY --from=styles /build/static/css ./static/css

# 앱은 root가 아닌 사용자로 돈다. 정적·미디어 디렉터리를 미리 만들어 두면
# 처음 붙는 named volume이 이 소유권을 물려받는다.
RUN useradd --system --uid 1000 --no-create-home app \
    && mkdir -p /app/staticfiles /app/media \
    && chown app:app /app/staticfiles /app/media
USER app

EXPOSE 8000
# 로컬 개발(compose.yaml)용 기본 명령. 프로덕션(compose.prod.yaml)은 gunicorn으로 덮어쓴다.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
