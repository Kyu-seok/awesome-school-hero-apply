"""신청 목록을 공유 스프레드시트로 내보낸다."""

from datetime import datetime

from django.utils import timezone

from applications.models import Application
from exports.models import SheetExport
from exports.sheets import Rows, get_sheet

HEADER = [
    "신청 ID",
    "접수 시각",
    "교육",
    "기관명",
    "신청자",
    "이메일",
    "연락처",
    "대상",
    "학급 수",
    "수업 형태",
    "수업 희망일",
    "연락 가능 날짜",
    "상태",
    "연락일 안내 발송 시각",
    "운영 메모",
]


def _local_minute(value: datetime | None) -> str:
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M") if value else ""


def _class_format(application: Application) -> str:
    unit = "교시" if application.class_type == Application.ClassType.SINGLE else "회차"
    return f"{application.get_class_type_display()} · {application.session_count}{unit}"


def _row(application: Application) -> list:
    return [
        application.pk,
        _local_minute(application.created_at),
        application.program.name,
        application.organization_name,
        application.applicant_name,
        application.applicant_email,
        application.applicant_phone,
        application.target_grade,
        application.class_count,
        _class_format(application),
        application.preferred_class_date.isoformat(),
        application.contact_date.isoformat(),
        application.get_status_display(),
        _local_minute(application.contact_day_email_sent_at),
        application.operator_memo,
    ]


def build_rows() -> Rows:
    """헤더와 전체 신청(신청 ID 순, 취소 포함)."""
    applications = Application.objects.select_related("program").order_by("pk")
    return [HEADER, *(_row(application) for application in applications)]


def export_applications() -> int:
    """공유 시트를 현재 전체 신청 목록으로 덮어쓴다. 쓴 신청 수를 돌려준다."""
    rows = build_rows()
    get_sheet().overwrite(rows)
    return len(rows) - 1


def start_export() -> SheetExport:
    """내보내기 요청을 기록한다. 결과는 finish_export나 fail_export가 채운다."""
    return SheetExport.objects.create()


def finish_export(export_id: int | None, row_count: int) -> None:
    SheetExport.objects.filter(pk=export_id).update(
        finished_at=timezone.now(), row_count=row_count, error=""
    )


def fail_export(export_id: int | None, error: str) -> None:
    SheetExport.objects.filter(pk=export_id).update(finished_at=timezone.now(), error=error)


def last_export() -> SheetExport | None:
    """가장 최근에 요청한 내보내기(없으면 None)."""
    return SheetExport.objects.first()
