"""Google Sheets 내보내기 (Seam 3). 인메모리 어댑터로 바꿔 끼우고 /manage/에서 실행한다."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from applications.models import Application
from exports.sheets import memory_sheet
from tests.factories import make_application, make_program

pytestmark = pytest.mark.django_db

KST = ZoneInfo("Asia/Seoul")
EXPORT_URL = "/manage/export/"
HEADER = [
    "신청 ID",
    "접수 시각",
    "교육",
    "기관명",
    "신청자",
    "이메일",
    "연락처",
    "대상",
    "학급 수",
    "수업 형태",
    "수업 희망일",
    "연락 가능 날짜",
    "상태",
    "연락일 안내 발송 시각",
    "운영 메모",
]


@pytest.fixture(autouse=True)
def in_memory_sheet(settings):
    settings.EXPORTS_SHEET_BACKEND = "memory"
    memory_sheet.rows = [["이전 내용"]]
    yield memory_sheet
    memory_sheet.rows = []


@pytest.fixture
def operator_client(client, django_user_model):
    client.force_login(
        django_user_model.objects.create_user("operator", password="pw", is_staff=True)
    )
    return client


def test_operator_export_overwrites_sheet_with_header_and_all_applications(operator_client):
    program = make_program(name="인공지능 챔피언")
    with time_machine.travel(datetime(2026, 11, 20, 14, 5, 30, tzinfo=KST), tick=False):
        first = make_application(
            program,
            organization_name="챔피언초등학교",
            applicant_name="김선생",
            applicant_email="kim@example.com",
            applicant_phone="010-1234-5678",
            target_grade="초등 5학년",
            class_count=3,
            class_type=Application.ClassType.SINGLE,
            session_count=6,
            preferred_class_date=date(2026, 12, 21),
            contact_date=date(2026, 11, 24),
        )
        second = make_application(
            program,
            organization_name="용감중학교",
            applicant_name="이선생",
            applicant_email="lee@example.com",
            applicant_phone="010-9999-0000",
            target_grade="중학 1학년",
            class_count=1,
            class_type=Application.ClassType.MULTI,
            session_count=4,
            preferred_class_date=date(2026, 12, 28),
            contact_date=date(2026, 11, 25),
            status=Application.Status.CONTACTED,
            operator_memo="12/1 재통화",
            contact_day_email_sent_at=datetime(2026, 11, 25, 9, 0, 3, tzinfo=KST),
        )

    response = operator_client.post(EXPORT_URL, follow=True)

    assert response.status_code == 200
    assert "내보내기를 시작했습니다" in response.content.decode()
    assert memory_sheet.rows == [
        HEADER,
        [
            first.pk,
            "2026-11-20 14:05",
            "인공지능 챔피언",
            "챔피언초등학교",
            "김선생",
            "kim@example.com",
            "010-1234-5678",
            "초등 5학년",
            3,
            "1회 · 6교시",
            "2026-12-21",
            "2026-11-24",
            "접수됨",
            "",
            "",
        ],
        [
            second.pk,
            "2026-11-20 14:05",
            "인공지능 챔피언",
            "용감중학교",
            "이선생",
            "lee@example.com",
            "010-9999-0000",
            "중학 1학년",
            1,
            "다회 · 4회차",
            "2026-12-28",
            "2026-11-25",
            "연락 완료",
            "2026-11-25 09:00",
            "12/1 재통화",
        ],
    ]


def test_exporting_again_replaces_previous_contents(operator_client):
    kept = make_application(organization_name="남는 기관")
    removed = make_application(organization_name="지워질 기관")
    operator_client.post(EXPORT_URL)
    removed.delete()

    operator_client.post(EXPORT_URL)

    assert memory_sheet.rows[0] == HEADER
    assert [row[3] for row in memory_sheet.rows[1:]] == ["남는 기관"]
    assert memory_sheet.rows[1][0] == kept.pk


def test_export_with_no_applications_writes_only_header(operator_client):
    operator_client.post(EXPORT_URL)

    assert memory_sheet.rows == [HEADER]


def test_list_page_offers_export_button(operator_client):
    page = operator_client.get("/manage/?tab=all").content.decode()

    assert f'action="{EXPORT_URL}"' in page
    assert "disabled" not in page.split(f'action="{EXPORT_URL}"')[1].split("</form>")[0]


def test_anonymous_user_cannot_export(client):
    make_application()

    response = client.post(EXPORT_URL)

    assert response.status_code == 302
    assert response["Location"].startswith("/manage/login/")
    assert memory_sheet.rows == [["이전 내용"]]


def test_regular_user_cannot_export(client, django_user_model):
    make_application()
    client.force_login(django_user_model.objects.create_user("someone", password="pw"))

    response = client.post(EXPORT_URL)

    assert response.status_code == 403
    assert memory_sheet.rows == [["이전 내용"]]


def test_export_requires_post(operator_client):
    response = operator_client.get(EXPORT_URL)

    assert response.status_code == 405
    assert memory_sheet.rows == [["이전 내용"]]


def test_export_returns_operator_to_the_page_they_were_on(operator_client):
    response = operator_client.post(EXPORT_URL, {"next": "/manage/?tab=all&status=received"})
    assert response["Location"] == "/manage/?tab=all&status=received"

    response = operator_client.post(EXPORT_URL, {"next": "https://evil.example.com/"})
    assert response["Location"] == "/manage/"


def test_export_without_configured_sheet_tells_operator_and_writes_nothing(
    operator_client, settings
):
    """배포(DEBUG 꺼짐)에서 EXPORTS_SHEET_BACKEND를 비우면 메모리에 조용히 쓰지 않고 알린다."""
    settings.EXPORTS_SHEET_BACKEND = ""
    make_application()

    response = operator_client.post(EXPORT_URL, follow=True)

    page = response.content.decode()
    assert "내보내기를 시작했습니다" not in page
    assert "시트 내보내기가 설정되지 않았습니다" in page
    assert memory_sheet.rows == [["이전 내용"]]


def test_export_with_incomplete_google_settings_tells_operator(operator_client, settings):
    settings.EXPORTS_SHEET_BACKEND = "google"
    settings.GOOGLE_SHEETS_SPREADSHEET_ID = ""

    response = operator_client.post(EXPORT_URL, follow=True)

    page = response.content.decode()
    assert "내보내기를 시작했습니다" not in page
    assert "시트 내보내기가 설정되지 않았습니다" in page


def _export_status(page: str) -> str:
    """목록 페이지의 "마지막 내보내기" 한 줄."""
    marker = "마지막 내보내기:"
    assert marker in page, page
    return " ".join(page.split(marker, 1)[1].split("<", 1)[0].split())


def test_list_page_shows_last_export_result(operator_client):
    make_application(organization_name="챔피언초등학교")
    make_application(organization_name="용감중학교")
    with time_machine.travel(datetime(2026, 12, 1, 10, 3, tzinfo=KST), tick=False):
        operator_client.post(EXPORT_URL)

    page = operator_client.get("/manage/").content.decode()

    assert _export_status(page) == "12/1 10:03 완료 · 2건"


def test_list_page_shows_failed_export(operator_client, settings, tmp_path):
    settings.EXPORTS_SHEET_BACKEND = "google"
    settings.GOOGLE_SHEETS_SPREADSHEET_ID = "sheet-id"
    settings.GOOGLE_SHEETS_CREDENTIALS_FILE = str(tmp_path / "missing-key.json")
    make_application()
    with time_machine.travel(datetime(2026, 12, 1, 10, 3, tzinfo=KST), tick=False):
        operator_client.post(EXPORT_URL)

    page = operator_client.get("/manage/").content.decode()

    assert _export_status(page) == "12/1 10:03 실패"
    assert "missing-key.json" in page


def test_list_page_shows_no_export_status_before_first_export(operator_client):
    page = operator_client.get("/manage/").content.decode()

    assert "마지막 내보내기:" not in page
