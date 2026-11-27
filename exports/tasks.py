"""내보내기 Celery 작업."""

import logging

from celery import shared_task

from exports import services

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 30


@shared_task(bind=True, max_retries=MAX_RETRIES)
def export_applications_to_sheet(self, export_id: int | None = None) -> None:
    """시트를 덮어쓰고 결과를 내보내기 기록(export_id)에 남긴다.

    네트워크 오류(OSError)는 30초, 60초 뒤 다시 시도하고, 그래도 실패하면 실패로 기록한다.
    """
    try:
        count = services.export_applications()
    except OSError as exc:
        if self.request.retries < MAX_RETRIES:
            raise self.retry(
                exc=exc, countdown=RETRY_BACKOFF_SECONDS * 2**self.request.retries
            ) from exc
        services.fail_export(export_id, _describe(exc))
        raise
    except Exception as exc:
        services.fail_export(export_id, _describe(exc))
        raise
    services.finish_export(export_id, count)
    logger.info("시트 내보내기 완료: 신청 %s건", count)


def _describe(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"
