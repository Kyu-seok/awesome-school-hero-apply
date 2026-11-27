"""접수 확인 메일: POST /api/applications/ 뒤 mail.outbox (Seam 1, HTTP 경계).

Celery 작업은 즉시 실행(conftest의 CELERY_TASK_ALWAYS_EAGER)으로 돌린다. 발송은 신청이 커밋된 뒤
예약되므로, 요청을 django_capture_on_commit_callbacks로 감싸 커밋 시점을 흉내 낸다.

날짜는 2026-12-01(화) 10:00 KST에 고정한다.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend

from applications.models import Application
from tests.factories import make_program

pytestmark = pytest.mark.django_db

KST = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 12, 1, 10, 0, tzinfo=KST)
URL = "/api/applications/"


class FailingEmailBackend(BaseEmailBackend):
    """SMTP 서버가 응답하지 않는 상황을 흉내 낸다."""

    def send_messages(self, email_messages):
        raise ConnectionRefusedError("SMTP 서버에 연결할 수 없습니다.")


@pytest.fixture(autouse=True)
def frozen_today():
    with time_machine.travel(NOW, tick=False):
        yield


@pytest.fixture
def program():
    return make_program(slug="hero", name="인공지능 히어로")


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
        "privacy_consent": True,
    }
    data.update(overrides)
    return data


def submit(api_client, capture, data):
    with capture(execute=True):
        return api_client.post(URL, data, format="json")


def test_received_application_sends_one_receipt_email_to_the_applicant(
    api_client, program, django_capture_on_commit_callbacks
):
    response = submit(api_client, django_capture_on_commit_callbacks, payload(program))

    assert response.status_code == 201
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["teacher@example.com"]
    assert "접수" in message.subject
    for text in ["인공지능 히어로", "히어로초등학교", "2026년 12월 22일", "12월 3일"]:
        assert text in message.body
    assert "12월 3일(목)에 담당자가 연락드립니다" in message.body


def test_receipt_email_has_an_html_version_with_the_same_details(
    api_client, program, django_capture_on_commit_callbacks
):
    submit(api_client, django_capture_on_commit_callbacks, payload(program))

    html, mimetype = mail.outbox[0].alternatives[0]
    assert mimetype == "text/html"
    for text in ["인공지능 히어로", "히어로초등학교", "2026년 12월 22일", "12월 3일(목)"]:
        assert text in html


def test_receipt_email_is_sent_only_after_the_application_commits(
    api_client, program, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        response = api_client.post(URL, payload(program), format="json")

    assert response.status_code == 201
    assert mail.outbox == []
    for callback in callbacks:
        callback()
    assert len(mail.outbox) == 1


def test_rejected_application_sends_no_email(
    api_client, program, django_capture_on_commit_callbacks
):
    response = submit(
        api_client,
        django_capture_on_commit_callbacks,
        payload(program, preferred_class_date="2026-12-10"),
    )

    assert response.status_code == 400
    assert mail.outbox == []


def test_duplicate_application_sends_no_second_email(
    api_client, program, django_capture_on_commit_callbacks
):
    submit(api_client, django_capture_on_commit_callbacks, payload(program))
    duplicate = submit(api_client, django_capture_on_commit_callbacks, payload(program))

    assert duplicate.status_code == 400
    assert len(mail.outbox) == 1


def test_honeypot_application_sends_no_email(
    api_client, program, django_capture_on_commit_callbacks
):
    response = submit(
        api_client,
        django_capture_on_commit_callbacks,
        payload(program, website="http://spam.example.com"),
    )

    assert response.status_code == 201
    assert mail.outbox == []


def test_failing_mail_server_does_not_fail_the_application(
    api_client, program, django_capture_on_commit_callbacks, settings
):
    settings.EMAIL_BACKEND = "tests.test_receipt_email.FailingEmailBackend"

    response = submit(api_client, django_capture_on_commit_callbacks, payload(program))

    assert response.status_code == 201
    assert Application.objects.filter(pk=response.json()["id"]).exists()
    assert mail.outbox == []
