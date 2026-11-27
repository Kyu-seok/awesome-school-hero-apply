"""Celery 앱. 설정은 Django settings의 CELERY_* 값에서 읽는다."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("hero_school")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
