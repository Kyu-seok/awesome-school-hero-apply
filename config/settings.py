"""Django settings. 모든 환경별 값은 환경변수로 받는다(.env.example 참고)."""

import os
from pathlib import Path

import dj_database_url
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-do-not-use-in-production")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "config.apps.SuperuserAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "programs",
    "applications",
    "backoffice",
    "notifications",
    "exports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# 기본값은 로컬 PostgreSQL(유닉스 소켓, 현재 OS 사용자). CI와 compose는 DATABASE_URL로 덮어쓴다.
DATABASES = {
    "default": dj_database_url.config(
        default="postgres:///hero_school", conn_max_age=60
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# 저장소 공용 정적 파일. static/css/는 SCSS 빌드 결과라 커밋하지 않는다(npm run build:css).
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "히어로스쿨 교육 신청 API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# 익명 신청 접수 throttle 비율(DRF 형식, 예: "10/hour").
APPLICATION_SUBMIT_THROTTLE_RATE = os.environ.get("APPLICATION_SUBMIT_THROTTLE_RATE", "10/hour")

# 랜딩 페이지(/)에서 보여줄 대표 교육의 슬러그.
LANDING_PROGRAM_SLUG = os.environ.get("LANDING_PROGRAM_SLUG", "ai-hero")

# 관리자 페이지(/manage/)는 Django 기본 로그인을 쓴다.
LOGIN_URL = "/manage/login/"
LOGIN_REDIRECT_URL = "/manage/"
LOGOUT_REDIRECT_URL = "/manage/login/"

# Celery. 로컬 compose와 배포에서는 redis 서비스를 브로커로 쓴다.
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_IGNORE_RESULT = True
# 브로커가 죽어 있어도 신청 API가 오래 붙잡히지 않게 발행 재시도를 짧게 끊는다.
CELERY_BROKER_CONNECTION_TIMEOUT = 2
CELERY_TASK_PUBLISH_RETRY_POLICY = {
    "max_retries": 2,
    "interval_start": 0,
    "interval_step": 0.5,
    "interval_max": 1,
}
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# beat 스케줄. crontab은 CELERY_TIMEZONE(Asia/Seoul) 기준이다.
CELERY_BEAT_SCHEDULE = {
    "send-todays-contact-day-emails": {
        "task": "notifications.tasks.send_todays_contact_day_emails",
        "schedule": crontab(hour=9, minute=0),
    },
}

# 메일. 로컬 기본값은 console 백엔드(worker 로그에 찍힌다). 테스트는 Django가 locmem으로 바꾼다.
# 배포는 Gmail SMTP: EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend와 앱 비밀번호.
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
# SMTP 서버가 느려도 worker가 한 메일에 오래 묶이지 않게 한다.
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "히어로스쿨 <kyuships@gmail.com>")

# 신청 목록 내보내기(스프레드시트). "memory"는 프로세스 메모리에만 쓴다(테스트, 로컬 기본값).
# 배포는 "google": 서비스 계정 JSON 키 경로(저장소 밖, 컨테이너에 마운트)와 시트 ID가 필요하다.
EXPORTS_SHEET_BACKEND = os.environ.get("EXPORTS_SHEET_BACKEND", "memory")
GOOGLE_SHEETS_CREDENTIALS_FILE = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE", "")
GOOGLE_SHEETS_SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "")
# 비우면 시트의 첫 번째 탭에 쓴다.
GOOGLE_SHEETS_WORKSHEET = os.environ.get("GOOGLE_SHEETS_WORKSHEET", "")
