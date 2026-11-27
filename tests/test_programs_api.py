import pytest

from tests.factories import make_curriculum_item, make_program

pytestmark = pytest.mark.django_db


def test_list_returns_only_published_programs(api_client):
    make_program(slug="open", name="공개 교육")
    make_program(slug="hidden", is_published=False)

    response = api_client.get("/api/programs/")

    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()]
    assert "open" in slugs
    assert "hidden" not in slugs


def test_detail_includes_curriculum_in_period_order(api_client):
    program = make_program(slug="ai", name="인공지능 교육")
    make_curriculum_item(program, period=2, title="두 번째")
    make_curriculum_item(program, period=1, title="첫 번째")
    make_curriculum_item(program, period=3, title="세 번째")

    response = api_client.get("/api/programs/ai/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "인공지능 교육"
    assert [item["period"] for item in body["curriculum"]] == [1, 2, 3]
    assert [item["title"] for item in body["curriculum"]] == ["첫 번째", "두 번째", "세 번째"]


def test_detail_of_unpublished_program_is_404(api_client):
    make_program(slug="hidden", is_published=False)

    response = api_client.get("/api/programs/hidden/")

    assert response.status_code == 404


def test_swagger_ui_opens(client):
    response = client.get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger" in response.content.lower()


def test_openapi_schema_lists_program_endpoints(client):
    response = client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    assert "/api/programs/{slug}/" in response.json()["paths"]
