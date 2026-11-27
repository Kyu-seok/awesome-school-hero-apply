"""신청 서비스 레이어. 신청의 도메인 규칙은 모두 여기에 있다.

API(serializer)와 관리자 페이지는 규칙을 다시 구현하지 않고 이 모듈의 진입점을 부른다.
"오늘"은 언제나 Asia/Seoul(TIME_ZONE) 기준 날짜다.

진입점
- receive_application: 신청 접수(검증, 중복 확인, 저장, 접수 확인 메일 예약)
- send_todays_contact_day_emails: 오늘의 연락일 안내 발송
- change_status: 상태 변경(운영자가 상태와 운영 메모를 바꾼다)
- date_limits: 오늘 받을 수 있는 가장 이른 수업 희망일과 연락 가능 날짜(신청 폼 안내용)
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from applications.models import Application
from notifications import emails
from notifications.tasks import schedule_receipt_email
from programs.models import Program

logger = logging.getLogger(__name__)

MIN_LEAD_DAYS = 21
MIN_CLASS_COUNT = 1
MAX_CLASS_COUNT = 35

DUPLICATE_MESSAGE = "이미 접수된 신청이 있습니다."


@dataclass(frozen=True)
class DateLimits:
    earliest_class_date: date
    earliest_contact_date: date


def date_limits(today: date | None = None) -> DateLimits:
    """오늘 신청하면 받아들여지는 가장 이른 수업 희망일과 연락 가능 날짜.

    연락 가능 날짜는 내일 이후의 첫 평일이다. 수업 희망일보다 앞서야 한다는 조건은
    수업 희망일을 고른 뒤에야 정해지므로 여기서 다루지 않는다.
    """
    today = today or timezone.localdate()
    contact = today + timedelta(days=1)
    while contact.weekday() >= 5:
        contact += timedelta(days=1)
    return DateLimits(
        earliest_class_date=today + timedelta(days=MIN_LEAD_DAYS),
        earliest_contact_date=contact,
    )


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
    """신청을 접수하고, 커밋 뒤 접수 확인 메일을 예약한다.

    규칙을 어기면 필드별 메시지를 담은 ValidationError를 던진다.

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

    earliest_class_date = date_limits(today).earliest_class_date
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
            application = Application.objects.create(
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
            schedule_receipt_email(application)
    except IntegrityError as exc:
        # 동시에 들어온 같은 신청: 먼저 확인했지만 DB 부분 유니크 제약이 최종 판정한다.
        if "unique_active_application" in str(exc):
            raise ValidationError({NON_FIELD_ERRORS: [DUPLICATE_MESSAGE]}) from exc
        raise
    return application


def send_todays_contact_day_emails() -> int:
    """오늘의 연락일 안내 발송. 보낸 메일 수를 돌려준다.

    대상은 연락 가능 날짜가 오늘이고, 접수됨 상태이고, 아직 안내를 받지 않은 신청이다.
    신청마다 따로 트랜잭션을 열고 행을 잠근 채 대상인지 다시 확인한 뒤 보내고 발송 시각을
    기록한다. 그래서 두 번 실행하거나 동시에 실행돼도 신청마다 한 통만 나간다.
    한 신청의 발송이 실패하면 그 신청의 트랜잭션만 되돌리고(발송 시각은 빈 채로 남아 다음
    실행 때 다시 대상이 된다) 나머지 신청은 계속 보낸다.
    """
    today = timezone.localdate()
    sent = 0
    for application_id in _contact_day_email_targets(today).values_list("pk", flat=True):
        try:
            with transaction.atomic():
                application = (
                    _contact_day_email_targets(today)
                    .select_related("program")
                    .select_for_update(skip_locked=True, of=("self",))
                    .filter(pk=application_id)
                    .first()
                )
                if application is None:
                    # 그사이 상태가 바뀌었거나, 이미 보냈거나, 다른 실행이 보내는 중이다.
                    continue
                emails.send_contact_day_email(application)
                application.contact_day_email_sent_at = timezone.now()
                application.save(update_fields=["contact_day_email_sent_at", "updated_at"])
            sent += 1
        except Exception:
            logger.exception("연락일 안내 메일 발송 실패: 신청 %s", application_id)
    return sent


def _contact_day_email_targets(today: date):
    return Application.objects.filter(
        contact_date=today,
        status=Application.Status.RECEIVED,
        contact_day_email_sent_at__isnull=True,
    )


def change_status(
    application: Application, *, status: str, operator_memo: str | None = None
) -> Application:
    """운영자가 신청 상태(와 운영 메모)를 바꾼다. 상태 간 전이 제약은 두지 않는다.

    operator_memo가 None이면 메모는 그대로 둔다. 알 수 없는 상태면 ValidationError를 던진다.
    연락 완료 등 접수됨이 아닌 상태가 되면 연락일 안내 발송 대상에서 자연히 빠진다.
    """
    if status not in Application.Status.values:
        raise ValidationError({"status": ["알 수 없는 상태입니다."]})
    application.status = status
    update_fields = ["status", "updated_at"]
    if operator_memo is not None:
        application.operator_memo = operator_memo
        update_fields.append("operator_memo")
    try:
        with transaction.atomic():
            application.save(update_fields=update_fields)
    except IntegrityError as exc:
        # 취소된 신청을 되살렸는데 같은 조건의 활성 신청이 이미 있는 경우.
        if "unique_active_application" in str(exc):
            raise ValidationError({"status": [DUPLICATE_MESSAGE]}) from exc
        raise
    return application


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
