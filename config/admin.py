from django.contrib.admin import AdminSite


class SuperuserAdminSite(AdminSite):
    """교육 콘텐츠용 Django admin. 운영자(is_staff)가 아니라 superuser만 들어온다."""

    site_header = "히어로스쿨 콘텐츠 관리"

    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser
