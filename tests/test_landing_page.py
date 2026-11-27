from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import pytest
import time_machine

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


def test_landing_page_shows_seeded_ai_champion_program(client):
    response = client.get("/")

    assert response.status_code == 200
    html = response.content.decode()
    assert "인공지능 챔피언" in html
    for period in range(1, 7):
        assert f"{period}교시" in html


def test_landing_page_is_404_when_featured_program_is_unpublished(client, settings):
    settings.LANDING_PROGRAM_SLUG = "hidden"
    make_program(slug="hidden", is_published=False)

    response = client.get("/")

    assert response.status_code == 404


def test_landing_page_has_application_form_for_the_featured_program(client, settings):
    settings.LANDING_PROGRAM_SLUG = "featured"
    make_program(slug="featured")

    response = client.get("/")

    html = response.content.decode()
    assert 'data-endpoint="/api/applications/"' in html
    assert 'name="program" value="featured"' in html
    for field in [
        "organization_name",
        "applicant_name",
        "applicant_email",
        "applicant_phone",
        "target_grade",
        "class_count",
        "class_type",
        "session_count",
        "preferred_class_date",
        "contact_date",
        "request_note",
        "privacy_consent",
        "website",
    ]:
        assert f'name="{field}"' in html
    assert "csrftoken" in response.cookies


class _Elements(HTMLParser):
    """랜딩 HTML에서 요소를 (태그, 속성, 조상 id 목록)으로 모은다."""

    VOID = {"area", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}

    def __init__(self):
        super().__init__()
        self.found = []
        self._open = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        ancestors = [a.get("id") for _, a in self._open if a.get("id")]
        self.found.append((tag, attrs, ancestors))
        if tag not in self.VOID:
            self._open.append((tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self._open) - 1, -1, -1):
            if self._open[i][0] == tag:
                del self._open[i:]
                break


def _elements(response):
    parser = _Elements()
    parser.feed(response.content.decode())
    return parser.found


def test_landing_page_cta_jumps_to_the_application_form(client):
    elements = _elements(client.get("/"))

    cta_targets = [
        a["href"] for tag, a, _ in elements if tag == "a" and "cta" in a.get("class", "").split()
    ]
    assert cta_targets, "신청 CTA 링크가 없다"
    target_id = cta_targets[0].removeprefix("#")
    assert cta_targets[0].startswith("#")
    assert any(
        tag == "form" and a.get("id") == "apply-form" and target_id in ancestors
        for tag, a, ancestors in elements
    ), "CTA가 가리키는 섹션 안에 신청 폼이 없다"


@time_machine.travel(datetime(2026, 11, 27, 10, 0, tzinfo=ZoneInfo("Asia/Seoul")), tick=False)
def test_landing_page_form_tells_the_earliest_dates_it_will_accept(client):
    # 2026-11-27은 금요일이다. 수업 희망일은 3주 뒤(12/18 금)부터,
    # 연락 가능 날짜는 내일 이후의 첫 평일(11/30 월)부터 받는다.
    response = client.get("/")

    inputs = {a.get("name"): a for tag, a, _ in _elements(response) if tag == "input"}
    assert inputs["preferred_class_date"]["min"] == "2026-12-18"
    assert inputs["contact_date"]["min"] == "2026-11-30"
    html = response.content.decode()
    assert "2026년 12월 18일(금)" in html
    assert "2026년 11월 30일(월)" in html


def test_landing_page_shows_the_drawn_illustration_until_an_image_is_uploaded(client, settings):
    settings.LANDING_PROGRAM_SLUG = "featured"
    program = make_program(slug="featured")

    images = [a for tag, a, _ in _elements(client.get("/")) if tag == "img" and a.get("alt")]
    assert images[0]["src"] == "/static/img/ai-champion.svg"

    program.image = "programs/uploaded.png"
    program.save()
    images = [a for tag, a, _ in _elements(client.get("/")) if tag == "img" and a.get("alt")]
    assert images[0]["src"] == "/media/programs/uploaded.png"
