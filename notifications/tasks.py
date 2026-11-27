"""안내 메일 Celery 작업."""

import logging
import smtplib

from celery import shared_task
from django.db import transaction

from applications.models import Application
from notifications import emails

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=60,
    max_retries=3,
)
def send_receipt_email(application_id: int) -> None:
    application = Application.objects.select_related("program").filter(pk=application_id).first()
    if application is None:
        logger.warning("접수 확인 메일: 신청 %s이(가) 없어 건너뜁니다.", application_id)
        return
    emails.send_receipt_email(application)


@shared_task
def send_todays_contact_day_emails() -> int:
    """Celery beat가 매일 09:00 KST에 부르는 "오늘의 연락일 안내 발송"."""
    # applications.services가 이 모듈을 import하므로 순환을 피해 여기서 부른다.
    from applications import services

    return services.send_todays_contact_day_emails()


def schedule_receipt_email(application: Application) -> None:
    """현재 트랜잭션이 커밋된 뒤 접수 확인 메일 발송을 예약한다.

    브로커에 닿지 못해도 신청은 이미 저장됐으므로 예외를 올리지 않고 기록만 남긴다.
    """
    application_id = application.pk

    def enqueue():
        try:
            send_receipt_email.delay(application_id)
        except Exception:
            logger.exception("접수 확인 메일 예약 실패: 신청 %s", application_id)

    transaction.on_commit(enqueue)
