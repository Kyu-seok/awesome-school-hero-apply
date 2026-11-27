from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from applications.filters import ApplicationFilterForm
from applications.models import Application
from applications.serializers import (
    HONEYPOT_FIELD,
    ApplicationReceiptSerializer,
    ApplicationSubmitSerializer,
    OperatorApplicationSerializer,
    honeypot_receipt,
)
from applications.throttles import ApplicationSubmitThrottle


class OperatorPagination(PageNumberPagination):
    page_size = 20


class ApplicationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """신청 API.

    - 신청 접수(POST)는 누구나 할 수 있고 익명 throttle이 걸린다.
    - 목록(GET)과 상태·메모 수정(PATCH)은 운영자(is_staff, 세션 인증)만 쓴다.
    """

    queryset = Application.objects.for_operator()
    # 세션 인증만 쓴다. 그래야 익명 요청이 401(Basic 인증 요구)이 아니라 403을 받는다.
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
    pagination_class = OperatorPagination
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return super().get_permissions()

    def get_throttles(self):
        if self.action == "create":
            return [ApplicationSubmitThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.action == "create":
            return ApplicationSubmitSerializer
        return OperatorApplicationSerializer

    def filter_queryset(self, queryset):
        if self.action != "list":
            return queryset
        form = ApplicationFilterForm(self.request.query_params)
        if not form.is_valid():
            raise ValidationError({field: list(errors) for field, errors in form.errors.items()})
        return form.filter(queryset)

    @extend_schema(responses={201: ApplicationReceiptSerializer})
    def create(self, request, *args, **kwargs):
        if request.data.get(HONEYPOT_FIELD):
            # 숨김 필드를 채운 요청은 봇이다. 검증도 저장도 하지 않고 성공처럼 응답한다.
            return Response(honeypot_receipt(request.data), status=status.HTTP_201_CREATED)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, enum=Application.Status.values),
            OpenApiParameter("program", OpenApiTypes.STR, description="교육 슬러그"),
            OpenApiParameter("contact_date", OpenApiTypes.DATE, description="연락 가능 날짜"),
        ]
    )
    def list(self, request, *args, **kwargs):
        """운영자 전용: 신청 목록(최신순). 상태, 교육, 연락 가능 날짜로 거른다."""
        return super().list(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """운영자 전용: 상태와 운영 메모만 바꾼다. 다른 필드는 무시된다."""
        return super().partial_update(request, *args, **kwargs)
