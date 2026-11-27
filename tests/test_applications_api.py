"""신청 접수: POST /api/applications/ (Seam 1, HTTP 경계).

날짜는 time-machine으로 2026-12-01(화) 10:00 KST에 고정한다.
- 오늘 + 21일 = 2026-12-22(화)
- 내일 = 2026-12-02(수)
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from applications.models import Application
from tests.factories import make_application, make_program

pytestmark = pytest.mark.django_db

KST = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 12, 1, 10, 0, tzinfo=KST)  # 화요일
URL = "/api/applications/"


@pytest.fixture(autouse=True)
def frozen_today():
    with time_machine.travel(NOW, tick=False):
        yield


@pytest.fixture
def program():
    return make_program(slug="hero")


def payload(program, **overrides):
    data = {
        "program": program.slug,
        "organization_name": "히어로초등학교",
        "applicant_name": "김선생",
        "applicant_email": "teacher@example.com",
        "applicant_phone": "010-1234-5678",
        "target_grade": "초등 5학년",
        "class_count": 3,
        "class_type": "single",
        "session_count": 6,
        "preferred_class_date": "2026-12-22",
        "contact_date": "2026-12-03",
        "request_note": "강당에서 진행하고 싶습니다.",
        "privacy_consent": True,
    }
    data.update(overrides)
    return data


def test_valid_application_is_received_with_its_contact_date(api_client, program):
    response = api_client.post(URL, payload(program), format="json")

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["status"] == "received"
    assert body["status_display"] == "접수됨"
    assert body["contact_date"] == "2026-12-03"
    saved = Application.objects.get(pk=body["id"])
    assert saved.organization_name == "히어로초등학교"
    assert saved.preferred_class_date == date(2026, 12, 22)
    assert saved.privacy_agreed_at == NOW


def test_preferred_class_date_must_be_at_least_21_days_ahead(api_client, program):
    too_soon = api_client.post(
        URL, payload(program, preferred_class_date="2026-12-21"), format="json"
    )
    just_in_time = api_client.post(
        URL, payload(program, preferred_class_date="2026-12-22"), format="json"
    )

    assert too_soon.status_code == 400
    assert "preferred_class_date" in too_soon.json()
    assert just_in_time.status_code == 201


def test_today_is_kst_even_when_utc_is_still_yesterday(api_client, program):
    # 2026-12-01 00:30 KST는 UTC로 11월 30일이다. 오늘은 KST 기준 12월 1일이어야 한다.
    with time_machine.travel(datetime(2026, 12, 1, 0, 30, tzinfo=KST), tick=False):
        response = api_client.post(
            URL, payload(program, preferred_class_date="2026-12-21"), format="json"
        )

    assert response.status_code == 400
    assert "preferred_class_date" in response.json()


@pytest.mark.parametrize(
    "contact_date",
    [
        pytest.param("2026-12-05", id="saturday"),
        pytest.param("2026-12-06", id="sunday"),
        pytest.param("2026-12-01", id="today"),
        pytest.param("2026-11-30", id="yesterday"),
        pytest.param("2026-12-22", id="on-preferred-class-date"),
        pytest.param("2026-12-23", id="after-preferred-class-date"),
    ],
)
def test_contact_date_outside_allowed_weekdays_is_rejected(api_client, program, contact_date):
    response = api_client.post(URL, payload(program, contact_date=contact_date), format="json")

    assert response.status_code == 400
    assert "contact_date" in response.json()


def test_contact_date_can_be_tomorrow(api_client, program):
    response = api_client.post(URL, payload(program, contact_date="2026-12-02"), format="json")

    assert response.status_code == 201


@pytest.mark.parametrize("consent", [False, None])
def test_privacy_consent_is_required(api_client, program, consent):
    data = payload(program, privacy_consent=consent)
    if consent is None:
        del data["privacy_consent"]

    response = api_client.post(URL, data, format="json")

    assert response.status_code == 400
    assert "privacy_consent" in response.json()


@pytest.mark.parametrize("class_count", [0, 36])
def test_class_count_must_be_between_1_and_35(api_client, program, class_count):
    response = api_client.post(URL, payload(program, class_count=class_count), format="json")

    assert response.status_code == 400
    assert "class_count" in response.json()


@pytest.mark.parametrize("class_count", [1, 35])
def test_class_count_bounds_are_accepted(api_client, program, class_count):
    response = api_client.post(URL, payload(program, class_count=class_count), format="json")

    assert response.status_code == 201


def test_missing_and_malformed_fields_are_reported_per_field(api_client, program):
    data = payload(program, applicant_email="not-an-email", class_type="weekly")
    del data["organization_name"]

    response = api_client.post(URL, data, format="json")

    assert response.status_code == 400
    assert set(response.json()) >= {"organization_name", "applicant_email", "class_type"}


def test_unpublished_program_cannot_be_applied_for(api_client):
    hidden = make_program(slug="hidden", is_published=False)

    response = api_client.post(URL, payload(hidden), format="json")

    assert response.status_code == 400
    assert "program" in response.json()


def test_same_email_program_and_preferred_class_date_is_a_duplicate(api_client, program):
    first = api_client.post(URL, payload(program), format="json")
    second = api_client.post(URL, payload(program, contact_date="2026-12-04"), format="json")

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.json()["non_field_errors"] == ["이미 접수된 신청이 있습니다."]


def test_duplicate_check_ignores_email_case(api_client, program):
    api_client.post(URL, payload(program), format="json")

    response = api_client.post(
        URL, payload(program, applicant_email="Teacher@Example.com"), format="json"
    )

    assert response.status_code == 400
    assert "non_field_errors" in response.json()


def test_different_preferred_class_date_or_program_is_not_a_duplicate(api_client, program):
    other_program = make_program(slug="other")
    api_client.post(URL, payload(program), format="json")

    other_date = api_client.post(
        URL, payload(program, preferred_class_date="2026-12-23"), format="json"
    )
    other_program_response = api_client.post(URL, payload(other_program), format="json")

    assert other_date.status_code == 201
    assert other_program_response.status_code == 201


def test_cancelled_application_does_not_block_reapplying(api_client, program):
    make_application(
        program=program,
        applicant_email="teacher@example.com",
        preferred_class_date=date(2026, 12, 22),
        status="cancelled",
    )

    response = api_client.post(URL, payload(program), format="json")

    assert response.status_code == 201


@pytest.mark.parametrize("status", ["received", "contacted", "confirmed"])
def test_active_application_in_any_other_status_blocks_reapplying(api_client, program, status):
    make_application(
        program=program,
        applicant_email="teacher@example.com",
        preferred_class_date=date(2026, 12, 22),
        status=status,
    )

    response = api_client.post(URL, payload(program), format="json")

    assert response.status_code == 400
    assert "non_field_errors" in response.json()


def test_honeypot_submission_looks_successful_but_is_not_saved(api_client, program):
    trapped = api_client.post(URL, payload(program, website="http://spam.example"), format="json")
    real = api_client.post(URL, payload(program), format="json")

    # 봇에게는 성공처럼 보인다. 저장되지 않았으므로 같은 조건의 진짜 신청은 중복이 아니다.
    assert trapped.status_code == 201
    assert real.status_code == 201
    assert Application.objects.count() == 1


def test_anonymous_submissions_are_throttled(api_client, program, settings):
    settings.APPLICATION_SUBMIT_THROTTLE_RATE = "2/minute"

    statuses = [
        api_client.post(
            URL, payload(program, preferred_class_date=f"2026-12-2{day}"), format="json"
        ).status_code
        for day in (2, 3, 4)
    ]

    assert statuses == [201, 201, 429]
