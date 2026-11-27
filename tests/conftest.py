import pytest
from rest_framework.test import APIClient

# Django 테스트 Client는 pytest-django의 `client` fixture를 그대로 쓴다.


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()
