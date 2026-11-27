from rest_framework.routers import DefaultRouter

from programs.api import ProgramViewSet

router = DefaultRouter(trailing_slash=True)
router.register("programs", ProgramViewSet, basename="program")

api_urlpatterns = router.urls
