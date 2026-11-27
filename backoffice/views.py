from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from applications import services
from applications.filters import ApplicationFilterForm
from applications.models import Application
from backoffice.access import operator_required
from backoffice.forms import StatusChangeForm

PAGE_SIZE = 20
TAB_TODAY = "today"
TAB_ALL = "all"


@operator_required
def application_list(request):
    """기본 탭은 오늘 연락할 신청(연락 가능 날짜가 오늘), "전체" 탭은 모든 신청. 둘 다 최신순."""
    tab = TAB_ALL if request.GET.get("tab") == TAB_ALL else TAB_TODAY
    queryset = Application.objects.select_related("program").order_by("-created_at", "-id")
    if tab == TAB_TODAY:
        queryset = queryset.filter(contact_date=timezone.localdate())

    filter_form = ApplicationFilterForm(request.GET)
    if filter_form.is_valid():
        queryset = filter_form.filter(queryset)
    else:
        queryset = queryset.none()

    page_obj = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "backoffice/application_list.html",
        {
            "tab": tab,
            "today": timezone.localdate(),
            "filter_form": filter_form,
            "page_obj": page_obj,
        },
    )


@operator_required
def application_detail(request, pk):
    """신청 상세. 모든 입력값을 보여주고, 상태와 운영 메모를 바꾼다."""
    application = get_object_or_404(Application.objects.select_related("program"), pk=pk)
    if request.method == "POST":
        form = StatusChangeForm(request.POST)
        if form.is_valid():
            try:
                services.change_status(
                    application,
                    status=form.cleaned_data["status"],
                    operator_memo=form.cleaned_data["operator_memo"],
                )
            except ValidationError as exc:
                for field, errors in exc.message_dict.items():
                    for error in errors:
                        form.add_error(field if field in form.fields else None, error)
            else:
                messages.success(request, "저장했습니다.")
                return redirect("backoffice:application-detail", pk=application.pk)
    else:
        form = StatusChangeForm(
            initial={"status": application.status, "operator_memo": application.operator_memo}
        )
    return render(
        request,
        "backoffice/application_detail.html",
        {"application": application, "form": form},
    )
