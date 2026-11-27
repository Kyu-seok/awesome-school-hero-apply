from rest_framework.routers import SimpleRouter

from applications.api import ApplicationViewSet

router = SimpleRouter(trailing_slash=True)
router.register("applications", ApplicationViewSet, basename="application")

api_urlpatterns = router.urls
