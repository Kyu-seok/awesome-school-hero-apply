"""운영자 API: GET/PATCH /api/applications/ (HTTP 경계). 세션 인증 + is_staff."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from applications.models import Application
from tests.factories import make_application, make_program

pytestmark = pytest.mark.django_db

KST = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 12, 1, 10, 0, tzinfo=KST)  # 화요일
TODAY = date(2026, 12, 1)
URL = "/api/applications/"


@pytest.fixture(autouse=True)
def frozen_today():
    with time_machine.travel(NOW, tick=False):
        yield


@pytest.fixture
def operator(django_user_model):
    return django_user_model.objects.create_user("operator", password="pw", is_staff=True)


@pytest.fixture
def operator_client(api_client, operator):
    api_client.force_login(operator)
    return api_client


def ids(response):
    return {row["id"] for row in response.json()["results"]}


def test_anonymous_user_gets_403_from_operator_api(api_client):
    application = make_application()

    assert api_client.get(URL).status_code == 403
    response = api_client.patch(f"{URL}{application.pk}/", {"status": "contacted"}, format="json")
    assert response.status_code == 403


def test_regular_user_gets_403_from_operator_api(api_client, django_user_model):
    application = make_application()
    api_client.force_login(django_user_model.objects.create_user("someone", password="pw"))

    assert api_client.get(URL).status_code == 403
    response = api_client.patch(f"{URL}{application.pk}/", {"status": "contacted"}, format="json")
    assert response.status_code == 403


def test_operator_lists_applications_newest_first_with_pagination(operator_client):
    older = make_application(organization_name="먼저 온 기관")
    newer = make_application(organization_name="나중 온 기관")

    response = operator_client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [row["id"] for row in body["results"]] == [newer.pk, older.pk]
    row = body["results"][0]
    assert row["organization_name"] == "나중 온 기관"
    assert row["status"] == "received"
    assert row["program"]["slug"] == newer.program.slug
    assert "privacy_agreed_at" in row
    assert "contact_day_email_sent_at" in row


def test_operator_api_paginates(operator_client):
    program = make_program()
    for _ in range(25):
        make_application(program)

    first = operator_client.get(URL).json()
    second = operator_client.get(URL, {"page": 2}).json()

    assert first["count"] == 25
    assert len(first["results"]) == 20
    assert len(second["results"]) == 5
    assert second["next"] is None


def test_operator_api_filters_by_status_program_and_contact_date(operator_client):
    champion = make_program(slug="champion")
    other = make_program(slug="other")
    match = make_application(champion, status="contacted", contact_date=date(2026, 12, 3))
    wrong_status = make_application(champion, status="received", contact_date=date(2026, 12, 3))
    wrong_program = make_application(other, status="contacted", contact_date=date(2026, 12, 3))
    wrong_date = make_application(champion, status="contacted", contact_date=date(2026, 12, 4))

    assert ids(operator_client.get(URL, {"status": "contacted"})) == {
        match.pk,
        wrong_program.pk,
        wrong_date.pk,
    }
    assert ids(operator_client.get(URL, {"program": "champion"})) == {
        match.pk,
        wrong_status.pk,
        wrong_date.pk,
    }
    assert ids(operator_client.get(URL, {"contact_date": "2026-12-04"})) == {wrong_date.pk}
    response = operator_client.get(
        URL, {"status": "contacted", "program": "champion", "contact_date": "2026-12-03"}
    )
    assert ids(response) == {match.pk}


def test_operator_api_rejects_invalid_filter_values(operator_client):
    response = operator_client.get(URL, {"status": "nope", "contact_date": "어제"})

    assert response.status_code == 400
    body = response.json()
    assert set(body) == {"status", "contact_date"}
    assert all(isinstance(message, str) for message in body["status"])


def test_operator_changes_status_and_memo_with_patch(operator_client):
    application = make_application()

    response = operator_client.patch(
        f"{URL}{application.pk}/",
        {"status": "contacted", "operator_memo": "12/3 통화. 강당 확인 필요."},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "contacted"
    row = operator_client.get(URL, {"status": "contacted"}).json()["results"][0]
    assert row["id"] == application.pk
    assert row["operator_memo"] == "12/3 통화. 강당 확인 필요."


def test_patch_cannot_change_fields_other_than_status_and_memo(operator_client):
    application = make_application(organization_name="원래 기관", contact_date=date(2026, 12, 3))
    other_program = make_program(slug="other")

    response = operator_client.patch(
        f"{URL}{application.pk}/",
        {
            "organization_name": "바꾼 기관",
            "contact_date": "2026-12-04",
            "program": other_program.slug,
            "applicant_email": "hacker@example.com",
            "contact_day_email_sent_at": "2026-12-01T09:00:00+09:00",
            "operator_memo": "메모만 바뀐다",
        },
        format="json",
    )

    assert response.status_code == 200
    row = operator_client.get(URL).json()["results"][0]
    assert row["organization_name"] == "원래 기관"
    assert row["contact_date"] == "2026-12-03"
    assert row["program"]["slug"] == application.program.slug
    assert row["applicant_email"] == application.applicant_email
    assert row["contact_day_email_sent_at"] is None
    assert row["operator_memo"] == "메모만 바뀐다"


def test_patch_rejects_unknown_status(operator_client):
    application = make_application()

    response = operator_client.patch(
        f"{URL}{application.pk}/", {"status": "deleted"}, format="json"
    )

    assert response.status_code == 400
    assert "status" in response.json()
    assert Application.objects.get(pk=application.pk).status == "received"


def test_application_submit_stays_public(api_client):
    # 운영자 API가 붙어도 신청 접수는 익명으로 할 수 있다(세부 규칙은 test_applications_api).
    response = api_client.post(URL, {}, format="json")
    assert response.status_code == 400
