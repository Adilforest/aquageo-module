from rest_framework.routers import DefaultRouter

from .views import ParseJobViewSet

router = DefaultRouter()
router.register("parse-jobs", ParseJobViewSet, basename="parsejob")

urlpatterns = router.urls
