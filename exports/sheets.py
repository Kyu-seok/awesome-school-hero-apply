"""스프레드시트 어댑터. 인터페이스는 "행 목록으로 시트 덮어쓰기" 하나다.

어느 구현을 쓸지는 설정 EXPORTS_SHEET_BACKEND로 고른다.
- "memory": 프로세스 메모리에 둔다(테스트, 로컬 기본값).
- "google": Google Sheets API를 서비스 계정으로 호출한다(배포).
"""

from typing import Protocol
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

Cell = str | int
Rows = list[list[Cell]]

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


class Sheet(Protocol):
    def overwrite(self, rows: Rows) -> None:
        """시트의 기존 내용을 지우고 rows를 A1부터 쓴다."""


class InMemorySheet:
    def __init__(self) -> None:
        self.rows: Rows = []

    def overwrite(self, rows: Rows) -> None:
        self.rows = [list(row) for row in rows]


memory_sheet = InMemorySheet()


class GoogleSheet:
    """서비스 계정 JSON 키로 인증해 시트 하나를 통째로 덮어쓴다.

    시트는 서비스 계정 이메일에 편집자로 공유되어 있어야 한다. worksheet가 비어 있으면
    첫 번째 탭을 쓴다.
    """

    def __init__(self, credentials_file: str, spreadsheet_id: str, worksheet: str = "") -> None:
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.worksheet = worksheet

    def _range(self, cells: str) -> str:
        if not self.worksheet:
            return cells
        quoted = self.worksheet.replace("'", "''")
        return f"'{quoted}'!{cells}"

    def overwrite(self, rows: Rows) -> None:
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_file, scopes=[SHEETS_SCOPE]
        )
        session = AuthorizedSession(credentials)
        base = f"{SHEETS_API}/{self.spreadsheet_id}/values"
        # 지우기와 쓰기를 한 번의 batch 요청으로 보낼 수 없어 순서대로 호출한다.
        session.post(
            f"{base}:batchClear", json={"ranges": [self._range("A:ZZ")]}, timeout=30
        ).raise_for_status()
        session.put(
            f"{base}/{quote(self._range('A1'), safe='')}",
            params={"valueInputOption": "RAW"},
            json={"values": rows},
            timeout=30,
        ).raise_for_status()


def get_sheet() -> Sheet:
    """설정에 맞는 시트. 설정이 비었거나 모자라면 ImproperlyConfigured를 던진다."""
    backend = settings.EXPORTS_SHEET_BACKEND
    if not backend:
        raise ImproperlyConfigured("EXPORTS_SHEET_BACKEND를 설정해야 합니다(google 또는 memory).")
    if backend == "memory":
        return memory_sheet
    if backend == "google":
        if not (settings.GOOGLE_SHEETS_CREDENTIALS_FILE and settings.GOOGLE_SHEETS_SPREADSHEET_ID):
            raise ImproperlyConfigured(
                "GOOGLE_SHEETS_CREDENTIALS_FILE와 GOOGLE_SHEETS_SPREADSHEET_ID를 설정해야 합니다."
            )
        return GoogleSheet(
            settings.GOOGLE_SHEETS_CREDENTIALS_FILE,
            settings.GOOGLE_SHEETS_SPREADSHEET_ID,
            settings.GOOGLE_SHEETS_WORKSHEET,
        )
    raise ImproperlyConfigured(f"알 수 없는 EXPORTS_SHEET_BACKEND: {backend!r}")
