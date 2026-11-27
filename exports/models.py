from django.db import models


class SheetExport(models.Model):
    """시트 내보내기 한 번의 기록. 관리자 페이지에 마지막 결과를 보여주려고 남긴다."""

    started_at = models.DateTimeField("요청 시각", auto_now_add=True)
    finished_at = models.DateTimeField("끝난 시각", null=True, blank=True)
    row_count = models.PositiveIntegerField("내보낸 신청 수", null=True, blank=True)
    error = models.TextField("실패 사유", blank=True)

    class Meta:
        verbose_name = "시트 내보내기"
        verbose_name_plural = "시트 내보내기"
        ordering = ["-started_at", "-id"]

    def __str__(self):
        return f"시트 내보내기 {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def is_running(self) -> bool:
        return self.finished_at is None

    @property
    def failed(self) -> bool:
        return bool(self.error)
