from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from applications.urls import api_urlpatterns as application_api
from programs.urls import api_urlpatterns as program_api
from programs.views import landing

urlpatterns = [
    path("", landing, name="landing"),
    path("admin/", admin.site.urls),
    path("api/", include(program_api)),
    path("api/", include(application_api)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
