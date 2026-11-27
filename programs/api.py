from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from programs.models import Program
from programs.serializers import ProgramDetailSerializer, ProgramListSerializer


class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """공개된 교육만 조회한다. 공개되지 않은 교육은 목록에 없고 상세는 404다."""

    queryset = Program.objects.published().prefetch_related("curriculum")
    lookup_field = "slug"
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProgramDetailSerializer
        return ProgramListSerializer
