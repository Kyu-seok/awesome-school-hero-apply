"""시드 데이터: "인공지능 히어로" 교육과 6교시 커리큘럼.

마이그레이션으로 넣어서 `migrate`만 하면 랜딩 페이지에 교육이 보인다.
update_or_create를 써서 다시 실행해도 안전하다. 운영 중 Django admin에서 바꾼 내용은
이 마이그레이션이 다시 돌지 않으므로 덮어써지지 않는다.

주의: 히어로스쿨 공식 커리큘럼 원문을 웹에서 확인하지 못했다. 아래 문구는 교육 취지에 맞춰
작성한 임시 콘텐츠다. 원문을 확인하면 새 데이터 마이그레이션으로 고치고 출처를 표기한다.
"""

from django.db import migrations

SLUG = "ai-hero"

PROGRAM = {
    "name": "인공지능 히어로",
    "summary": "AI를 쓰는 사람에서 AI로 문제를 해결하는 히어로로",
    "description": (
        "인공지능 히어로는 학생들이 생성형 AI의 원리를 이해하고, 책임감 있게 활용해 "
        "우리 주변의 문제를 해결해 보는 프로젝트형 교육입니다.\n\n"
        "학생들은 AI가 어떻게 배우고 답하는지 직접 체험하고, AI가 틀릴 수 있다는 점과 "
        "윤리적 쟁점을 토론합니다. 마지막에는 팀별로 AI를 활용한 문제 해결 아이디어를 "
        "만들어 발표합니다."
    ),
    "audience": "초등 5학년 ~ 고등학생 (학급 단위)",
    "class_format": "1회 6교시 집중형 또는 다회차(회당 2교시) 운영",
    "is_published": True,
}

CURRICULUM = [
    (1, "AI 히어로 출동 준비", "우리 생활 속 인공지능을 찾아보고, AI가 무엇을 잘하고 못하는지 이야기합니다."),
    (2, "AI는 어떻게 배울까?", "분류 놀이와 간단한 머신러닝 체험으로 데이터가 AI를 만든다는 것을 이해합니다."),
    (3, "생성형 AI와 대화하기", "좋은 질문(프롬프트)이 좋은 답을 만든다는 것을 실습으로 익힙니다."),
    (4, "AI의 그림자 탐정단", "AI의 오류, 편향, 저작권과 개인정보 문제를 사례로 살펴보고 토론합니다."),
    (5, "AI로 문제 해결 프로젝트", "팀별로 학교와 지역의 문제를 고르고 AI를 활용한 해결 아이디어를 설계합니다."),
    (6, "히어로 발표회", "팀별 아이디어를 발표하고 피드백을 나누며 AI 히어로 선언문을 작성합니다."),
]


def seed(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    CurriculumItem = apps.get_model("programs", "CurriculumItem")
    program, _ = Program.objects.update_or_create(slug=SLUG, defaults=PROGRAM)
    for period, title, description in CURRICULUM:
        CurriculumItem.objects.update_or_create(
            program=program, period=period, defaults={"title": title, "description": description}
        )


def unseed(apps, schema_editor):
    apps.get_model("programs", "Program").objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [("programs", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
