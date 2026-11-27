from django.conf import settings
from django.shortcuts import get_object_or_404, render

from applications import services
from programs.models import Program


def landing(request):
    """대표 교육 소개 페이지. 어느 교육을 보여줄지는 LANDING_PROGRAM_SLUG 설정으로 정한다."""
    program = get_object_or_404(
        Program.objects.published().prefetch_related("curriculum"),
        slug=settings.LANDING_PROGRAM_SLUG,
    )
    return render(
        request,
        "programs/landing.html",
        {
            "program": program,
            "date_limits": services.date_limits(),
            "min_class_count": services.MIN_CLASS_COUNT,
            "max_class_count": services.MAX_CLASS_COUNT,
            "min_lead_weeks": services.MIN_LEAD_WEEKS,
        },
    )
