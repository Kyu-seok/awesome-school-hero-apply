"""테스트 데이터 factory 함수. 필수값은 기본값으로 채우고, 테스트가 신경 쓰는 값만 넘긴다."""

from datetime import timedelta
from itertools import count

from django.utils import timezone

from applications.models import Application
from programs.models import CurriculumItem, Program

_seq = count(1)


def make_program(**overrides) -> Program:
    n = next(_seq)
    fields = {
        "slug": f"program-{n}",
        "name": f"테스트 교육 {n}",
        "summary": "한 줄 소개",
        "description": "상세 소개",
        "audience": "초등 5학년 ~ 중학생",
        "class_format": "1회 6교시",
        "is_published": True,
    }
    fields.update(overrides)
    return Program.objects.create(**fields)


def make_curriculum_item(program: Program, period: int, **overrides) -> CurriculumItem:
    fields = {"title": f"{period}교시 제목", "description": f"{period}교시 설명"}
    fields.update(overrides)
    return CurriculumItem.objects.create(program=program, period=period, **fields)


def make_application(program: Program | None = None, **overrides) -> Application:
    n = next(_seq)
    fields = {
        "program": program or make_program(),
        "organization_name": f"테스트 기관 {n}",
        "applicant_name": "신청자",
        "applicant_email": f"applicant{n}@example.com",
        "applicant_phone": "010-0000-0000",
        "target_grade": "초등 5학년",
        "class_count": 2,
        "class_type": Application.ClassType.SINGLE,
        "session_count": 6,
        "preferred_class_date": timezone.localdate() + timedelta(days=30),
        "contact_date": timezone.localdate() + timedelta(days=7),
        "privacy_agreed_at": timezone.now(),
    }
    fields.update(overrides)
    return Application.objects.create(**fields)
