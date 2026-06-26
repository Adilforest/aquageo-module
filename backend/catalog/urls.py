from django.urls import path
from rest_framework.routers import DefaultRouter

from .stats_views import (
    ByConditionView,
    ByTerritoryView,
    ByTypeView,
    LevelTimeseriesView,
    RegionsView,
    RiskSummaryView,
)
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

urlpatterns = router.urls + [
    path("stats/by-type/", ByTypeView.as_view(), name="stats-by-type"),
    path("stats/by-condition/", ByConditionView.as_view(), name="stats-by-condition"),
    path("stats/by-territory/", ByTerritoryView.as_view(), name="stats-by-territory"),
    path("stats/risk-summary/", RiskSummaryView.as_view(), name="stats-risk-summary"),
    path("stats/level-timeseries/", LevelTimeseriesView.as_view(), name="stats-level-timeseries"),
    path("regions/", RegionsView.as_view(), name="regions"),
]
