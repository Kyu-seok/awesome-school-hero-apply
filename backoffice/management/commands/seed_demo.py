"""데모 운영자 계정과 데모 신청을 넣는다. 여러 번 실행해도 결과가 같다.

- 운영자: DEMO_OPERATOR_USERNAME / DEMO_OPERATOR_PASSWORD(환경변수). is_staff지만 superuser가
  아니어서 Django admin(/admin/)에는 들어갈 수 없다.
- 신청: 신청자 이메일(@demo.heroschool.example)로 식별해 덮어쓴다. 날짜는 실행한 날(KST)
  기준으로 다시 계산하므로, 다시 실행하면 "오늘 연락할 신청"이 늘 채워진다.
  도메인 규칙(3주 전 신청 등)은 데모 상황을 만들려고 일부러 건너뛴다.
"""

import os
from datetime import datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from applications.models import Application
from programs.models import Program

DEFAULT_USERNAME = "demo-operator"
DEFAULT_PASSWORD = "hero-demo-2026"
DEMO_EMAIL_DOMAIN = "demo.heroschool.example"
CONTACT_DAY_EMAIL_TIME = time(9, 0)

S = Application.Status
SINGLE, MULTI = Application.ClassType.SINGLE, Application.ClassType.MULTI

# (기관명, 신청자, 학년, 학급 수, 수업 형태, 교시/회차, 수업 희망일 오프셋, 연락 가능 날짜 오프셋,
#  상태, 운영 메모, 연락일 안내 발송 여부)
# fmt: off
DEMO_APPLICATIONS = [
    ("서울챔피언초등학교", "김하늘", "초등 5학년", 4, SINGLE, 6, 28, 0, S.RECEIVED, "", True),
    ("부산바다중학교", "이준호", "중학 1학년", 6, MULTI, 4, 35, 0, S.RECEIVED, "", True),
    ("대전과학초등학교", "박서연", "초등 6학년", 3, SINGLE, 6, 30, 0, S.CONTACTED,
     "연락일 전에 먼저 통화함. 12시 이후 연락 선호.", False),
    ("광주빛고을초등학교", "최민준", "초등 4학년", 2, SINGLE, 4, 40, 1, S.RECEIVED, "", False),
    ("인천미래중학교", "정수아", "중학 2학년", 8, MULTI, 6, 45, 2, S.RECEIVED, "", False),
    ("수원창의지역아동센터", "강지우", "초등 3~6학년 혼합", 1, SINGLE, 3, 33, 3, S.RECEIVED,
     "", False),
    ("대구달빛초등학교", "윤서준", "초등 5학년", 5, SINGLE, 6, 24, -1, S.CONTACTED,
     "통화 완료. 컴퓨터실 대수 확인 후 회신 예정.", True),
    ("울산바람중학교", "임하은", "중학 3학년", 7, MULTI, 8, 22, -3, S.CONFIRMED,
     "12월 수업 확정. 강사 2명 배정.", True),
    ("세종새롬초등학교", "한도윤", "초등 6학년", 4, SINGLE, 6, 26, -2, S.CONFIRMED,
     "수업 확정. 학급별 태블릿 준비됨.", True),
    ("제주한라초등학교", "오지민", "초등 5학년", 2, SINGLE, 6, 50, -4, S.CANCELLED,
     "학교 일정 변경으로 취소. 내년 1학기에 다시 신청 예정.", True),
    ("춘천호반중학교", "서예준", "중학 1학년", 5, MULTI, 4, 38, 4, S.RECEIVED, "", False),
    ("전주한옥초등학교", "신유나", "초등 4학년", 3, SINGLE, 4, 42, -1, S.CANCELLED,
     "중복 신청이라 취소.", False),
]
# fmt: on


class Command(BaseCommand):
    help = "데모 운영자 계정과 데모 신청 데이터를 넣는다(여러 번 실행해도 결과가 같다)."

    @transaction.atomic
    def handle(self, *args, **options):
        username = os.environ.get("DEMO_OPERATOR_USERNAME", DEFAULT_USERNAME)
        password = os.environ.get("DEMO_OPERATOR_PASSWORD", DEFAULT_PASSWORD)
        self._seed_operator(username, password)
        program = self._demo_program()
        count = self._seed_applications(program)
        self.stdout.write(
            self.style.SUCCESS(f"데모 운영자 '{username}'와 데모 신청 {count}건을 넣었습니다.")
        )

    def _seed_operator(self, username: str, password: str) -> None:
        user, _ = get_user_model().objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = False
        user.is_active = True
        if not user.check_password(password):
            # 비밀번호가 같으면 다시 해시하지 않는다. 다시 해시하면 로그인한 세션이 끊긴다.
            user.set_password(password)
        user.save()

    def _demo_program(self) -> Program:
        program = (
            Program.objects.filter(slug=settings.LANDING_PROGRAM_SLUG).first()
            or Program.objects.published().order_by("pk").first()
        )
        if program is None:
            raise CommandError("데모 신청을 붙일 교육이 없습니다. 교육을 먼저 만드세요.")
        return program

    def _seed_applications(self, program: Program) -> int:
        today = timezone.localdate()
        now = timezone.now()
        kst = timezone.get_current_timezone()
        for n, row in enumerate(DEMO_APPLICATIONS, start=1):
            (
                org,
                name,
                grade,
                classes,
                class_type,
                sessions,
                class_offset,
                contact_offset,
                status,
                memo,
                email_sent,
            ) = row
            contact_date = today + timedelta(days=contact_offset)
            Application.objects.update_or_create(
                applicant_email=f"demo{n:02d}@{DEMO_EMAIL_DOMAIN}",
                defaults={
                    "program": program,
                    "organization_name": org,
                    "applicant_name": name,
                    "applicant_phone": f"010-0000-{n:04d}",
                    "target_grade": grade,
                    "class_count": classes,
                    "class_type": class_type,
                    "session_count": sessions,
                    "preferred_class_date": today + timedelta(days=class_offset),
                    "contact_date": contact_date,
                    "request_note": "데모 신청입니다.",
                    "privacy_agreed_at": now - timedelta(days=7),
                    "status": status,
                    "operator_memo": memo,
                    "contact_day_email_sent_at": (
                        datetime.combine(contact_date, CONTACT_DAY_EMAIL_TIME, tzinfo=kst)
                        if email_sent and contact_offset <= 0
                        else None
                    ),
                },
            )
        return len(DEMO_APPLICATIONS)
