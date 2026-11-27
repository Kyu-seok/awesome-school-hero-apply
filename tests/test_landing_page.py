import pytest

from tests.factories import make_curriculum_item, make_program

pytestmark = pytest.mark.django_db


def test_landing_page_shows_featured_program_with_curriculum_in_order(client, settings):
    settings.LANDING_PROGRAM_SLUG = "featured"
    program = make_program(slug="featured", name="대표 교육", summary="대표 한 줄 소개")
    make_curriculum_item(program, period=2, title="둘째 교시")
    make_curriculum_item(program, period=1, title="첫째 교시")

    response = client.get("/")

    assert response.status_code == 200
    html = response.content.decode()
    assert "대표 교육" in html
    assert "대표 한 줄 소개" in html
    assert html.index("첫째 교시") < html.index("둘째 교시")


def test_landing_page_shows_seeded_ai_hero_program(client):
    response = client.get("/")

    assert response.status_code == 200
    html = response.content.decode()
    assert "인공지능 히어로" in html
    for period in range(1, 7):
        assert f"{period}교시" in html


def test_landing_page_is_404_when_featured_program_is_unpublished(client, settings):
    settings.LANDING_PROGRAM_SLUG = "hidden"
    make_program(slug="hidden", is_published=False)

    response = client.get("/")

    assert response.status_code == 404
