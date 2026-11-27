"""운영자 목록 필터. 관리자 페이지와 운영자 API가 같은 필터를 쓴다."""

from django import forms
from django.db.models import QuerySet

from applications.models import Application
from programs.models import Program


class ApplicationFilterForm(forms.Form):
    """상태, 교육(슬러그), 연락 가능 날짜로 신청을 거른다. 빈 값은 거르지 않는다."""

    status = forms.ChoiceField(
        label="상태",
        required=False,
        choices=[("", "전체 상태"), *Application.Status.choices],
    )
    program = forms.ModelChoiceField(
        label="교육",
        required=False,
        queryset=Program.objects.order_by("name"),
        to_field_name="slug",
        empty_label="전체 교육",
    )
    contact_date = forms.DateField(
        label="연락 가능 날짜",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def filter(self, queryset: QuerySet[Application]) -> QuerySet[Application]:
        """is_valid()를 부른 뒤에 쓴다."""
        data = self.cleaned_data
        if data.get("status"):
            queryset = queryset.filter(status=data["status"])
        if data.get("program"):
            queryset = queryset.filter(program=data["program"])
        if data.get("contact_date"):
            queryset = queryset.filter(contact_date=data["contact_date"])
        return queryset
