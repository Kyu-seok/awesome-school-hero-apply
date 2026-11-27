import pytest

from tests.factories import make_curriculum_item, make_program

pytestmark = pytest.mark.django_db


def test_superuser_can_edit_program_and_curriculum(client, django_user_model):
    admin = django_user_model.objects.create_superuser("root", password="pw")
    client.force_login(admin)
    program = make_program(slug="ai", name="옛 이름")
    item = make_curriculum_item(program, period=1, title="옛 제목")

    response = client.post(
        f"/admin/programs/program/{program.pk}/change/",
        {
            "slug": "ai",
            "name": "새 이름",
            "summary": program.summary,
            "description": program.description,
            "audience": program.audience,
            "class_format": program.class_format,
            "is_published": "on",
            "curriculum-TOTAL_FORMS": "2",
            "curriculum-INITIAL_FORMS": "1",
            "curriculum-MIN_NUM_FORMS": "0",
            "curriculum-MAX_NUM_FORMS": "1000",
            "curriculum-0-id": item.pk,
            "curriculum-0-program": program.pk,
            "curriculum-0-period": "1",
            "curriculum-0-title": "새 제목",
            "curriculum-0-description": "",
            "curriculum-1-program": program.pk,
            "curriculum-1-period": "2",
            "curriculum-1-title": "추가한 교시",
            "curriculum-1-description": "",
        },
    )

    assert response.status_code == 302
    detail = client.get("/api/programs/ai/").json()
    assert detail["name"] == "새 이름"
    assert [(i["period"], i["title"]) for i in detail["curriculum"]] == [
        (1, "새 제목"),
        (2, "추가한 교시"),
    ]


def test_staff_who_is_not_superuser_cannot_open_admin(client, django_user_model):
    operator = django_user_model.objects.create_user("operator", password="pw", is_staff=True)
    client.force_login(operator)

    response = client.get("/admin/programs/program/")

    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]
