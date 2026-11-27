"""안내 메일 작성과 발송.

템플릿은 notifications/templates/notifications/에 텍스트와 HTML 한 쌍씩 둔다.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from applications.dates import korean_date
from applications.models import Application


def send_receipt_email(application: Application) -> None:
    """접수 확인 메일: 신청 내용과 연락 가능 날짜를 신청자에게 확인해 준다."""
    context = {
        "application": application,
        "program_name": application.program.name,
        "preferred_class_date": korean_date(application.preferred_class_date),
        "contact_date": korean_date(application.contact_date, with_year=False),
    }
    _send(
        template="notifications/receipt",
        subject=f"[챔피언스쿨] {application.program.name} 교육 신청이 접수되었습니다",
        to=application.applicant_email,
        context=context,
    )


def send_contact_day_email(application: Application) -> None:
    """연락일 안내 메일: 오늘 운영자가 연락한다고 알리고 교육을 요약해 준다.

    메일 본문은 신청자가 읽으므로 운영자를 "담당자"라고 부른다(GLOSSARY.md).
    """
    program = application.program
    context = {
        "application": application,
        "program": program,
        "preferred_class_date": korean_date(application.preferred_class_date),
        "contact_date": korean_date(application.contact_date, with_year=False),
    }
    _send(
        template="notifications/contact_day",
        subject=f"[챔피언스쿨] 오늘 {program.name} 교육 신청 건으로 연락드립니다",
        to=application.applicant_email,
        context=context,
    )


def _send(*, template: str, subject: str, to: str, context: dict) -> None:
    message = EmailMultiAlternatives(
        subject=subject,
        body=render_to_string(f"{template}.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )
    message.attach_alternative(render_to_string(f"{template}.html", context), "text/html")
    message.send()
