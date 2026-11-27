"""테스트 데이터 factory 함수. 필수값은 기본값으로 채우고, 테스트가 신경 쓰는 값만 넘긴다."""

from itertools import count

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
