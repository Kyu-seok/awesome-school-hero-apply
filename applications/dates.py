"""날짜 규칙과 한국어 날짜 표기. 신청 서비스와 안내 메일이 같이 쓴다.

(신청 폼 apply-form.js에 같은 표기를 하는 작은 JS 사본이 있다.)
"""

from datetime import date, timedelta

WEEKDAYS = "월화수목금토일"


def is_weekday(day: date) -> bool:
    """월~금이면 True."""
    return day.weekday() < 5


def next_weekday_after(day: date) -> date:
    """day 다음 날부터 세어 첫 평일."""
    day += timedelta(days=1)
    while not is_weekday(day):
        day += timedelta(days=1)
    return day


def korean_date(day: date, *, with_year: bool = True, with_weekday: bool = True) -> str:
    """예: 2026년 12월 3일(목). with_year=False면 12월 3일(목), with_weekday=False면 요일을 뺀다."""
    text = f"{day.month}월 {day.day}일"
    if with_year:
        text = f"{day.year}년 {text}"
    if with_weekday:
        text = f"{text}({WEEKDAYS[day.weekday()]})"
    return text
