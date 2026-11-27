"""seed_demo 관리 명령: 데모 운영자 계정과 데모 신청. 결과는 HTTP 경계에서 확인한다."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.core.management import call_command

pytestmark = pytest.mark.django_db

KST = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 12, 1, 10, 0, tzinfo=KST)
DEMO_USERNAME = "demo-operator"
DEMO_PASSWORD = "seed-test-password"


@pytest.fixture(autouse=True)
def frozen_today():
    with time_machine.travel(NOW, tick=False):
        yield


@pytest.fixture(autouse=True)
def demo_password(monkeypatch):
    monkeypatch.setenv("DEMO_OPERATOR_PASSWORD", DEMO_PASSWORD)


def all_applications(client):
    response = client.get("/api/applications/")
    assert response.status_code == 200
    return response.json()


def test_seed_creates_demo_operator_and_demo_applications(client):
    call_command("seed_demo")

    assert client.login(username=DEMO_USERNAME, password=DEMO_PASSWORD)
    body = all_applications(client)
    assert 10 <= body["count"] <= 15
    statuses = {row["status"] for row in body["results"]}
    assert statuses == {"received", "contacted", "confirmed", "cancelled"}
    # 기본 탭(오늘 연락할 신청)이 비어 있지 않다.
    today_tab = client.get("/manage/")
    assert len(today_tab.context["page_obj"]) >= 1


def test_demo_operator_cannot_enter_django_admin(client):
    call_command("seed_demo")
    client.login(username=DEMO_USERNAME, password=DEMO_PASSWORD)

    response = client.get("/admin/")

    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def test_running_seed_twice_does_not_duplicate_demo_data(client, django_user_model):
    call_command("seed_demo")
    call_command("seed_demo")

    assert django_user_model.objects.filter(username=DEMO_USERNAME).count() == 1
    client.login(username=DEMO_USERNAME, password=DEMO_PASSWORD)
    first_ids = {row["id"] for row in all_applications(client)["results"]}
    call_command("seed_demo")
    assert {row["id"] for row in all_applications(client)["results"]} == first_ids
    assert 10 <= len(first_ids) <= 15
