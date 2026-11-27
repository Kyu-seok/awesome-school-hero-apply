"""관리자 페이지 /manage/ (HTTP 경계, 서버 렌더링). is_staff만 들어온다."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from tests.factories import make_application, make_program

pytestmark = pytest.mark.django_db

KST = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 12, 1, 10, 0, tzinfo=KST)  # 화요일
TODAY = date(2026, 12, 1)
URL = "/manage/"


@pytest.fixture(autouse=True)
def frozen_today():
    with time_machine.travel(NOW, tick=False):
        yield


@pytest.fixture
def operator(django_user_model):
    return django_user_model.objects.create_user("operator", password="pw", is_staff=True)


@pytest.fixture
def operator_client(client, operator):
    client.force_login(operator)
    return client


def test_anonymous_user_is_redirected_to_login(client):
    application = make_application()

    for url in (URL, f"{URL}applications/{application.pk}/"):
        response = client.get(url)
        assert response.status_code == 302
        assert response["Location"].startswith("/manage/login/?next=")


def test_regular_user_gets_403(client, django_user_model):
    application = make_application()
    client.force_login(django_user_model.objects.create_user("someone", password="pw"))

    assert client.get(URL).status_code == 403
    assert client.get(f"{URL}applications/{application.pk}/").status_code == 403
    response = client.post(f"{URL}applications/{application.pk}/", {"status": "contacted"})
    assert response.status_code == 403


def test_operator_logs_in_with_django_login_and_lands_on_manage(client, operator):
    page = client.get("/manage/login/")
    assert page.status_code == 200

    response = client.post("/manage/login/", {"username": "operator", "password": "pw"})

    assert response.status_code == 302
    assert response["Location"] == URL
    assert client.get(URL).status_code == 200


def listed(response):
    return {application.pk for application in response.context["page_obj"]}


def test_default_tab_shows_only_applications_to_contact_today(operator_client):
    today = make_application(organization_name="오늘 연락 기관", contact_date=TODAY)
    make_application(organization_name="내일 연락 기관", contact_date=date(2026, 12, 2))

    response = operator_client.get(URL)

    assert response.status_code == 200
    assert listed(response) == {today.pk}
    html = response.content.decode()
    assert "오늘 연락 기관" in html
    assert "내일 연락 기관" not in html


def test_all_tab_lists_every_application_newest_first(operator_client):
    older = make_application(contact_date=TODAY)
    newer = make_application(contact_date=date(2026, 12, 2))

    response = operator_client.get(URL, {"tab": "all"})

    assert [a.pk for a in response.context["page_obj"]] == [newer.pk, older.pk]


def test_list_filters_by_status_program_and_contact_date(operator_client):
    champion = make_program(slug="champion")
    other = make_program(slug="other")
    match = make_application(champion, status="contacted", contact_date=date(2026, 12, 3))
    make_application(champion, status="received", contact_date=date(2026, 12, 3))
    make_application(other, status="contacted", contact_date=date(2026, 12, 3))
    make_application(champion, status="contacted", contact_date=date(2026, 12, 4))

    response = operator_client.get(
        URL,
        {"tab": "all", "status": "contacted", "program": "champion", "contact_date": "2026-12-03"},
    )

    assert listed(response) == {match.pk}


def test_list_is_paginated(operator_client):
    program = make_program()
    for _ in range(25):
        make_application(program)

    first = operator_client.get(URL, {"tab": "all"})
    second = operator_client.get(URL, {"tab": "all", "page": 2})

    assert len(listed(first)) == 20
    assert len(listed(second)) == 5


def test_detail_shows_all_inputs_consent_time_and_contact_day_email_time(operator_client):
    application = make_application(
        organization_name="챔피언초등학교",
        applicant_name="김선생",
        applicant_email="teacher@example.com",
        applicant_phone="010-1234-5678",
        target_grade="초등 5학년",
        class_count=3,
        session_count=6,
        preferred_class_date=date(2026, 12, 22),
        contact_date=date(2026, 12, 3),
        request_note="강당에서 진행하고 싶습니다.",
        privacy_agreed_at=datetime(2026, 11, 30, 14, 5, tzinfo=KST),
        contact_day_email_sent_at=datetime(2026, 12, 3, 9, 0, tzinfo=KST),
    )

    html = operator_client.get(f"{URL}applications/{application.pk}/").content.decode()

    for text in [
        "챔피언초등학교",
        "김선생",
        "teacher@example.com",
        "010-1234-5678",
        "초등 5학년",
        "강당에서 진행하고 싶습니다.",
        application.program.name,
        "2026-12-22",
        "2026-12-03",
        "2026-11-30 14:05",  # 동의 시각
        "2026-12-03 09:00",  # 연락일 안내 메일 발송 시각
        "접수됨",
    ]:
        assert text in html, text


def test_operator_marks_contacted_and_saves_memo_from_detail(operator_client, api_client):
    application = make_application(contact_date=TODAY)
    detail = f"{URL}applications/{application.pk}/"

    response = operator_client.post(
        detail, {"status": "contacted", "operator_memo": "통화 완료. 12/22 강당."}
    )

    assert response.status_code == 302
    page = operator_client.get(detail).content.decode()
    assert "통화 완료. 12/22 강당." in page
    assert "저장했습니다" in page
    # 같은 상태가 운영자 API에도 보인다.
    row = operator_client.get("/api/applications/", {"status": "contacted"}).json()["results"]
    assert [r["id"] for r in row] == [application.pk]
    assert row[0]["operator_memo"] == "통화 완료. 12/22 강당."


def test_detail_form_rejects_unknown_status(operator_client):
    application = make_application()

    response = operator_client.post(
        f"{URL}applications/{application.pk}/", {"status": "deleted", "operator_memo": "x"}
    )

    assert response.status_code == 200
    assert response.context["form"].errors["status"]
    application.refresh_from_db()
    assert application.status == "received"
    assert application.operator_memo == ""
