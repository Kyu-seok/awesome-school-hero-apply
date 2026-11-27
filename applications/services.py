"""신청 서비스 레이어. 신청의 도메인 규칙은 모두 여기에 있다.

API(serializer)와 관리자 페이지는 규칙을 다시 구현하지 않고 이 모듈의 진입점을 부른다.
"오늘"은 언제나 Asia/Seoul(TIME_ZONE) 기준 날짜다.

진입점
- receive_application: 신청 접수(검증, 중복 확인, 저장)
"""

from datetime import date, timedelta

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from applications.models import Application
from programs.models import Program

MIN_LEAD_DAYS = 21
MIN_CLASS_COUNT = 1
MAX_CLASS_COUNT = 35

DUPLICATE_MESSAGE = "이미 접수된 신청이 있습니다."


def receive_application(
    *,
    program: Program,
    organization_name: str,
    applicant_name: str,
    applicant_email: str,
    applicant_phone: str,
    target_grade: str,
    class_count: int,
    class_type: str,
    session_count: int,
    preferred_class_date: date,
    contact_date: date,
    privacy_consent: bool,
    request_note: str = "",
) -> Application:
    """신청을 접수한다. 규칙을 어기면 필드별 메시지를 담은 ValidationError를 던진다.

    중복(같은 이메일, 교육, 수업 희망일의 취소되지 않은 신청)은 NON_FIELD_ERRORS로 알린다.
    """
    today = timezone.localdate()
    errors: dict[str, list[str]] = {}

    if not program.is_published:
        errors.setdefault("program", []).append("신청할 수 없는 교육입니다.")

    if not MIN_CLASS_COUNT <= class_count <= MAX_CLASS_COUNT:
        errors.setdefault("class_count", []).append(
            f"학급 수는 {MIN_CLASS_COUNT}~{MAX_CLASS_COUNT} 사이여야 합니다."
        )

    earliest_class_date = today + timedelta(days=MIN_LEAD_DAYS)
    if preferred_class_date < earliest_class_date:
        errors.setdefault("preferred_class_date", []).append(
            f"수업 희망일은 신청일로부터 3주 뒤인 {_format(earliest_class_date)} 이후여야 합니다. "
            "수업 준비에 3주가 필요합니다."
        )

    errors_for_contact_date = _contact_date_errors(contact_date, preferred_class_date, today)
    if errors_for_contact_date:
        errors["contact_date"] = errors_for_contact_date

    if not privacy_consent:
        errors.setdefault("privacy_consent", []).append("개인정보 수집·이용에 동의해야 합니다.")

    if errors:
        raise ValidationError(errors)

    if _has_active_duplicate(program, applicant_email, preferred_class_date):
        raise ValidationError({NON_FIELD_ERRORS: [DUPLICATE_MESSAGE]})

    try:
        with transaction.atomic():
            return Application.objects.create(
                program=program,
                organization_name=organization_name,
                applicant_name=applicant_name,
                applicant_email=applicant_email,
                applicant_phone=applicant_phone,
                target_grade=target_grade,
                class_count=class_count,
                class_type=class_type,
                session_count=session_count,
                preferred_class_date=preferred_class_date,
                contact_date=contact_date,
                request_note=request_note,
                privacy_agreed_at=timezone.now(),
            )
    except IntegrityError as exc:
        # 동시에 들어온 같은 신청: 먼저 확인했지만 DB 부분 유니크 제약이 최종 판정한다.
        if "unique_active_application" in str(exc):
            raise ValidationError({NON_FIELD_ERRORS: [DUPLICATE_MESSAGE]}) from exc
        raise


def _contact_date_errors(contact_date: date, preferred_class_date: date, today: date) -> list[str]:
    errors = []
    if contact_date <= today:
        errors.append("연락 가능 날짜는 내일 이후여야 합니다.")
    if contact_date >= preferred_class_date:
        errors.append("연락 가능 날짜는 수업 희망일보다 앞서야 합니다.")
    if contact_date.weekday() >= 5:
        errors.append("연락 가능 날짜는 평일(월~금)이어야 합니다.")
    return errors


def _has_active_duplicate(program: Program, email: str, preferred_class_date: date) -> bool:
    return (
        Application.objects.filter(
            program=program,
            applicant_email__iexact=email,
            preferred_class_date=preferred_class_date,
        )
        .exclude(status=Application.Status.CANCELLED)
        .exists()
    )


def _format(day: date) -> str:
    return f"{day.year}년 {day.month}월 {day.day}일"
