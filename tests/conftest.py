import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from config.celery import app

# Django 테스트 Client는 pytest-django의 `client` fixture를 그대로 쓴다.


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_cache():
    # throttle 기록이 locmem 캐시에 남아 다른 테스트로 새지 않게 한다.
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _celery_eager():
    # Celery 작업을 브로커 없이 그 자리에서 실행한다(Django 테스트 러너의 locmem 메일과 짝).
    previous = app.conf.task_always_eager
    app.conf.task_always_eager = True
    yield
    app.conf.task_always_eager = previous
