from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from applications.models import Application
from applications.serializers import (
    HONEYPOT_FIELD,
    ApplicationReceiptSerializer,
    ApplicationSubmitSerializer,
)
from applications.throttles import ApplicationSubmitThrottle


class ApplicationViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """신청 API. 신청 접수(POST)는 누구나 할 수 있고 익명 throttle이 걸린다."""

    queryset = Application.objects.all()
    serializer_class = ApplicationSubmitSerializer

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return super().get_permissions()

    def get_throttles(self):
        if self.action == "create":
            return [ApplicationSubmitThrottle()]
        return super().get_throttles()

    @extend_schema(responses={201: ApplicationReceiptSerializer})
    def create(self, request, *args, **kwargs):
        if request.data.get(HONEYPOT_FIELD):
            # 숨김 필드를 채운 요청은 봇이다. 검증도 저장도 하지 않고 성공처럼 응답한다.
            fake = {
                "id": None,
                "status": Application.Status.RECEIVED,
                "status_display": Application.Status.RECEIVED.label,
                "contact_date": request.data.get("contact_date"),
            }
            return Response(fake, status=status.HTTP_201_CREATED)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
