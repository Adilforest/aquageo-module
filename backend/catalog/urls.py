from rest_framework.routers import DefaultRouter

from .views import (
    AdminUnitViewSet,
    BasinViewSet,
    ObjectTypeViewSet,
    StructureViewSet,
    WaterBodyViewSet,
)

router = DefaultRouter()
router.register("structures", StructureViewSet, basename="structure")
router.register("basins", BasinViewSet, basename="basin")
router.register("admin-units", AdminUnitViewSet, basename="adminunit")
router.register("object-types", ObjectTypeViewSet, basename="objecttype")
router.register("water-bodies", WaterBodyViewSet, basename="waterbody")

urlpatterns = router.urls
