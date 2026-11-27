from django.db import models
from django.db.models.functions import Lower

from programs.models import Program


class Application(models.Model):
    """신청: 한 기관이 하나의 교육을 특정 수업 희망일에 받고 싶다고 접수한 요청.

    도메인 규칙(날짜, 중복, 상태)은 applications.services가 가진다.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", "접수됨"
        CONTACTED = "contacted", "연락 완료"
        CONFIRMED = "confirmed", "수업 확정"
        CANCELLED = "cancelled", "취소"

    class ClassType(models.TextChoices):
        SINGLE = "single", "1회"
        MULTI = "multi", "다회"

    program = models.ForeignKey(
        Program, on_delete=models.PROTECT, related_name="applications", verbose_name="교육"
    )
    organization_name = models.CharField("기관명", max_length=100)
    applicant_name = models.CharField("신청자 이름", max_length=50)
    applicant_email = models.EmailField("신청자 이메일")
    applicant_phone = models.CharField("신청자 연락처", max_length=30)
    target_grade = models.CharField("수업 대상(학년)", max_length=50)
    class_count = models.PositiveSmallIntegerField("학급 수")
    class_type = models.CharField("수업 형태", max_length=10, choices=ClassType.choices)
    session_count = models.PositiveSmallIntegerField("교시 수 또는 회차 수")
    preferred_class_date = models.DateField("수업 희망일")
    contact_date = models.DateField("연락 가능 날짜")
    request_note = models.TextField("요청 사항", blank=True)
    privacy_agreed_at = models.DateTimeField("개인정보 동의 시각")
    status = models.CharField(
        "상태", max_length=20, choices=Status.choices, default=Status.RECEIVED
    )
    operator_memo = models.TextField("운영 메모", blank=True)
    contact_day_email_sent_at = models.DateTimeField(
        "연락일 안내 메일 발송 시각", null=True, blank=True
    )
    created_at = models.DateTimeField("접수 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)

    class Meta:
        verbose_name = "신청"
        verbose_name_plural = "신청"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                Lower("applicant_email"),
                "program",
                "preferred_class_date",
                condition=~models.Q(status="cancelled"),
                name="unique_active_application",
            ),
            models.CheckConstraint(
                condition=models.Q(class_count__gte=1, class_count__lte=35),
                name="class_count_between_1_and_35",
            ),
        ]
        indexes = [
            models.Index(fields=["contact_date", "status"], name="application_contact_status"),
        ]

    def __str__(self):
        return f"{self.organization_name} · {self.program} · {self.preferred_class_date}"
