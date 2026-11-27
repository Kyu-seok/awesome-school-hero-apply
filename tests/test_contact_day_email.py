"""연락일 안내 메일: "오늘의 연락일 안내 발송" 진입점 (Seam 2).

time-machine으로 날짜를 2026-12-03(목) 09:00 KST에 고정하고 진입점을 직접 부른다.
발송 결과는 mail.outbox와 신청에 남은 연락일 안내 메일 발송 시각으로 확인한다.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend as LocmemEmailBackend

from applications.models import Application
from applications.services import send_todays_contact_day_emails
from tests.factories import make_application, make_program

pytestmark = pytest.mark.django_db

KST = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 12, 3, 9, 0, tzinfo=KST)
TODAY = date(2026, 12, 3)


class RejectsBrokenAddressBackend(LocmemEmailBackend):
    """broken@example.com으로 가는 메일만 SMTP 오류로 실패시키고 나머지는 outbox에 담는다."""

    def send_messages(self, messages):
        if any("broken@example.com" in message.to for message in messages):
            raise ConnectionRefusedError("SMTP 서버가 응답하지 않습니다.")
        return super().send_messages(messages)


@pytest.fixture(autouse=True)
def frozen_today():
    with time_machine.travel(NOW, tick=False):
        yield


@pytest.fixture
def program():
    return make_program(name="인공지능 히어로", summary="AI와 함께 문제를 해결하는 히어로 되기")


def contact_today(program, **overrides):
    return make_application(program, contact_date=TODAY, **overrides)


def recipients():
    return sorted(address for message in mail.outbox for address in message.to)


def test_sends_contact_day_email_to_received_applications_contacted_today(program):
    application = contact_today(
        program, applicant_email="teacher@example.com", organization_name="히어로초등학교"
    )

    send_todays_contact_day_emails()

    assert recipients() == ["teacher@example.com"]
    message = mail.outbox[0]
    assert "오늘 담당자가 연락드립니다" in message.body
    for text in ["인공지능 히어로", "AI와 함께 문제를 해결하는 히어로 되기", "히어로초등학교"]:
        assert text in message.body
    html, mimetype = message.alternatives[0]
    assert mimetype == "text/html"
    assert "오늘 담당자가 연락드립니다" in html
    application.refresh_from_db()
    assert application.contact_day_email_sent_at == NOW


@pytest.mark.parametrize(
    "status",
    [Application.Status.CONTACTED, Application.Status.CONFIRMED, Application.Status.CANCELLED],
)
def test_skips_applications_no_longer_received(program, status):
    skipped = contact_today(program, status=status)

    send_todays_contact_day_emails()

    assert mail.outbox == []
    skipped.refresh_from_db()
    assert skipped.contact_day_email_sent_at is None


def test_skips_applications_whose_contact_date_is_not_today(program):
    contact_today(program, applicant_email="today@example.com")
    make_application(
        program, applicant_email="tomorrow@example.com", contact_date=date(2026, 12, 4)
    )
    make_application(
        program, applicant_email="yesterday@example.com", contact_date=date(2026, 12, 2)
    )

    send_todays_contact_day_emails()

    assert recipients() == ["today@example.com"]


def test_running_twice_sends_one_email_per_application(program):
    contact_today(program, applicant_email="a@example.com")
    contact_today(program, applicant_email="b@example.com")

    send_todays_contact_day_emails()
    send_todays_contact_day_emails()

    assert recipients() == ["a@example.com", "b@example.com"]


def test_one_failing_email_does_not_stop_the_others_and_stays_eligible(program, settings):
    settings.EMAIL_BACKEND = "tests.test_contact_day_email.RejectsBrokenAddressBackend"
    contact_today(program, applicant_email="a@example.com")
    broken = contact_today(program, applicant_email="broken@example.com")
    contact_today(program, applicant_email="c@example.com")

    send_todays_contact_day_emails()

    assert recipients() == ["a@example.com", "c@example.com"]
    broken.refresh_from_db()
    assert broken.contact_day_email_sent_at is None

    # 메일 서버가 돌아온 뒤 다시 실행하면 실패했던 신청만 받는다.
    broken.applicant_email = "fixed@example.com"
    broken.save()
    mail.outbox.clear()
    send_todays_contact_day_emails()

    assert recipients() == ["fixed@example.com"]


def test_operator_marking_contacted_before_the_contact_date_prevents_the_email(
    program, api_client, django_user_model
):
    application = contact_today(program, applicant_email="early@example.com")
    operator = django_user_model.objects.create_user("operator", password="pw", is_staff=True)
    api_client.force_login(operator)

    # 연락 가능 날짜 이틀 전, 운영자가 미리 통화하고 연락 완료로 바꾼다.
    with time_machine.travel(datetime(2026, 12, 1, 15, 0, tzinfo=KST), tick=False):
        response = api_client.patch(
            f"/api/applications/{application.pk}/", {"status": "contacted"}, format="json"
        )
    assert response.status_code == 200

    send_todays_contact_day_emails()

    assert mail.outbox == []
    application.refresh_from_db()
    assert application.contact_day_email_sent_at is None


def test_failed_email_is_retried_by_a_later_run_the_same_day(program, settings):
    settings.EMAIL_BACKEND = "tests.test_contact_day_email.RejectsBrokenAddressBackend"
    application = contact_today(program, applicant_email="broken@example.com")

    send_todays_contact_day_emails()  # 09:00: 메일 서버 오류
    assert mail.outbox == []

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    retried_at = datetime(2026, 12, 3, 10, 0, tzinfo=KST)
    with time_machine.travel(retried_at, tick=False):
        send_todays_contact_day_emails()  # 10:00: 같은 날 다음 실행

    assert recipients() == ["broken@example.com"]
    application.refresh_from_db()
    assert application.contact_day_email_sent_at == retried_at


def test_email_that_failed_all_day_is_not_sent_the_next_day(program, settings):
    settings.EMAIL_BACKEND = "tests.test_contact_day_email.RejectsBrokenAddressBackend"
    application = contact_today(program, applicant_email="broken@example.com")
    send_todays_contact_day_emails()

    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    with time_machine.travel(datetime(2026, 12, 4, 9, 0, tzinfo=KST), tick=False):
        send_todays_contact_day_emails()

    assert mail.outbox == []
    application.refresh_from_db()
    assert application.contact_day_email_sent_at is None


def test_beat_runs_contact_day_emails_hourly_from_9_to_17_kst(settings):
    entry = settings.CELERY_BEAT_SCHEDULE["send-todays-contact-day-emails"]

    assert entry["task"] == "notifications.tasks.send_todays_contact_day_emails"
    assert entry["schedule"].hour == set(range(9, 18))
    assert entry["schedule"].minute == {0}
    assert settings.CELERY_TIMEZONE == "Asia/Seoul"
