import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

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
