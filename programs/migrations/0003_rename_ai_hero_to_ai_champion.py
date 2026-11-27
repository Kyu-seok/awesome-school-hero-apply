"""데모 교육 이름 바꾸기: "인공지능 히어로"(ai-hero) → "인공지능 챔피언"(ai-champion).

히어로스쿨은 실제로 운영 중인 서비스 이름이라, 데모 서비스는 챔피언스쿨로, 데모 교육은
"인공지능 챔피언"으로 부른다. 0002는 이미 배포 DB에서 실행됐으므로 고치지 않고, 그 행을
제자리에서 바꾼다. id가 그대로라 기존 신청의 교육 FK는 유지된다.

다시 실행해도 안전하다: ai-hero 행이 없으면 ai-champion 행을 같은 값으로 다시 맞춘다.
"""

from django.db import migrations

OLD_SLUG = "ai-hero"
NEW_SLUG = "ai-champion"

NEW_PROGRAM = {
    "name": "인공지능 챔피언",
    "summary": "AI를 쓰는 사람에서 AI로 문제를 해결하는 챔피언으로",
    "description": (
        "인공지능 챔피언은 학생들이 생성형 AI의 원리를 이해하고, 책임감 있게 활용해 "
        "우리 주변의 문제를 해결해 보는 프로젝트형 교육입니다.\n\n"
        "학생들은 AI가 어떻게 배우고 답하는지 직접 체험하고, AI가 틀릴 수 있다는 점과 "
        "윤리적 쟁점을 토론합니다. 마지막에는 팀별로 AI를 활용한 문제 해결 아이디어를 "
        "만들어 발표합니다."
    ),
}

OLD_PROGRAM = {
    "name": "인공지능 히어로",
    "summary": "AI를 쓰는 사람에서 AI로 문제를 해결하는 히어로로",
    "description": (
        "인공지능 히어로는 학생들이 생성형 AI의 원리를 이해하고, 책임감 있게 활용해 "
        "우리 주변의 문제를 해결해 보는 프로젝트형 교육입니다.\n\n"
        "학생들은 AI가 어떻게 배우고 답하는지 직접 체험하고, AI가 틀릴 수 있다는 점과 "
        "윤리적 쟁점을 토론합니다. 마지막에는 팀별로 AI를 활용한 문제 해결 아이디어를 "
        "만들어 발표합니다."
    ),
}

# 이름에 히어로가 들어간 교시만 바꾼다: (교시, 새 제목, 새 설명, 옛 제목, 옛 설명)
CURRICULUM = [
    (
        1,
        "AI 챔피언 출동 준비",
        "우리 생활 속 인공지능을 찾아보고, AI가 무엇을 잘하고 못하는지 이야기합니다.",
        "AI 히어로 출동 준비",
        "우리 생활 속 인공지능을 찾아보고, AI가 무엇을 잘하고 못하는지 이야기합니다.",
    ),
    (
        6,
        "챔피언 발표회",
        "팀별 아이디어를 발표하고 피드백을 나누며 AI 챔피언 선언문을 작성합니다.",
        "히어로 발표회",
        "팀별 아이디어를 발표하고 피드백을 나누며 AI 히어로 선언문을 작성합니다.",
    ),
]


def _rename(apps, from_slug, to_slug, program_fields, curriculum):
    Program = apps.get_model("programs", "Program")
    CurriculumItem = apps.get_model("programs", "CurriculumItem")
    program = (
        Program.objects.filter(slug=from_slug).first()
        or Program.objects.filter(slug=to_slug).first()
    )
    if program is None:
        return
    program.slug = to_slug
    for field, value in program_fields.items():
        setattr(program, field, value)
    program.save()
    for period, title, description in curriculum:
        CurriculumItem.objects.filter(program=program, period=period).update(
            title=title, description=description
        )


def forward(apps, schema_editor):
    curriculum = [(period, title, desc) for period, title, desc, _, _ in CURRICULUM]
    _rename(apps, OLD_SLUG, NEW_SLUG, NEW_PROGRAM, curriculum)


def backward(apps, schema_editor):
    curriculum = [(period, title, desc) for period, _, _, title, desc in CURRICULUM]
    _rename(apps, NEW_SLUG, OLD_SLUG, OLD_PROGRAM, curriculum)


class Migration(migrations.Migration):
    dependencies = [("programs", "0002_seed_ai_hero")]

    operations = [migrations.RunPython(forward, backward)]
