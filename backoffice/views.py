import logging

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from applications import services
from applications.filters import ApplicationFilterForm
from applications.models import Application
from backoffice.access import operator_required
from backoffice.forms import StatusChangeForm
from exports.sheets import get_sheet
from exports.tasks import export_applications_to_sheet

logger = logging.getLogger(__name__)

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


@require_POST
@operator_required
def export_to_sheet(request):
    """공유 시트 내보내기를 Celery 작업으로 맡기고 바로 목록으로 돌아간다.

    시트 설정이 비었거나 모자라면 작업을 맡기지 않고 운영자에게 바로 알린다.
    """
    try:
        get_sheet()
    except ImproperlyConfigured as exc:
        logger.error("시트 내보내기 설정 오류: %s", exc)
        messages.error(request, f"시트 내보내기가 설정되지 않았습니다: {exc}")
        return _back_to_list(request)
    try:
        export_applications_to_sheet.delay()
    except Exception:
        logger.exception("시트 내보내기 작업 예약 실패")
        messages.error(request, "내보내기를 시작하지 못했습니다. 잠시 뒤 다시 시도해 주세요.")
    else:
        messages.success(request, "내보내기를 시작했습니다. 잠시 뒤 시트에서 확인하세요.")
    return _back_to_list(request)


def _back_to_list(request):
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("backoffice:application-list")
