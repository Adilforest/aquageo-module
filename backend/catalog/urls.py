from rest_framework.routers import DefaultRouter

from .views import StructureViewSet

router = DefaultRouter()
router.register("structures", StructureViewSet, basename="structure")

urlpatterns = router.urls
