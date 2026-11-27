from django import forms

from applications.models import Application


class StatusChangeForm(forms.Form):
    """상세 화면의 상태 변경·운영 메모 폼. 저장은 services.change_status가 한다."""

    status = forms.ChoiceField(label="상태", choices=Application.Status.choices)
    operator_memo = forms.CharField(label="운영 메모", required=False, widget=forms.Textarea)
