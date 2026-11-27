"""내보내기 Celery 작업."""

import logging

from celery import shared_task

from exports import services

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(OSError,), retry_backoff=30, max_retries=2)
def export_applications_to_sheet() -> None:
    count = services.export_applications()
    logger.info("시트 내보내기 완료: 신청 %s건", count)
