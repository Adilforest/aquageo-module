"""Dashboard aggregate endpoints (issue #20).

All aggregates honor the same filters as the map (type/condition/basin/district/
search) so the dashboard and map stay consistent. Aggregation is done in the DB,
not on the client.
"""
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from assessment.models import ConditionAssessment
from monitoring.models import HydropostReading

from .filters import StructureFilter
from .models import ConditionStatus, Structure

CONDITIONS = [c.value for c in ConditionStatus]

FILTER_PARAMS = [
    OpenApiParameter("type", str, many=True),
    OpenApiParameter("condition", str, many=True),
    OpenApiParameter("basin", str),
    OpenApiParameter("district", str),
    OpenApiParameter("search", str),
]


def filtered_structures(request):
    """Apply the map filters (type/condition/basin/district/search) to Structure."""
    qs = StructureFilter(request.GET, queryset=Structure.objects.all()).qs
    search = request.GET.get("search")
    if search:
        qs = qs.filter(
            Q(name_ru__icontains=search)
            | Q(name_kk__icontains=search)
            | Q(name_en__icontains=search)
            | Q(cadastral_number__icontains=search)
        )
    return qs


class ByTypeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=FILTER_PARAMS, responses=OpenApiTypes.OBJECT)
    def get(self, request):
        rows = (
            filtered_structures(request)
            .values("type_id", "type__name_ru")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response([
            {"type": r["type_id"], "type_name": r["type__name_ru"], "count": r["count"]}
            for r in rows
        ])


class ByConditionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=FILTER_PARAMS, responses=OpenApiTypes.OBJECT)
    def get(self, request):
        qs = filtered_structures(request)
        counts = {c: 0 for c in CONDITIONS}
        for row in qs.values("condition_status").annotate(n=Count("id")):
            if row["condition_status"] in counts:
                counts[row["condition_status"]] = row["n"]
        total = sum(counts.values())
        healthy = counts["serviceable"] + counts["monitoring"]
        index = round(100 * healthy / total) if total else 0
        return Response({"counts": counts, "total": total, "index": index})


class ByTerritoryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[*FILTER_PARAMS, OpenApiParameter("group", str, enum=["basin", "district"])],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        group = request.GET.get("group", "basin")
        if group == "district":
            id_field, name_field = "admin_unit_id", "admin_unit__name_ru"
        else:
            group = "basin"
            id_field, name_field = "basin_id", "basin__name_ru"
        rows = (
            filtered_structures(request)
            .filter(**{f"{id_field}__isnull": False})
            .values(id_field, name_field)
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response({
            "group": group,
            "items": [
                {"id": str(r[id_field]), "name": r[name_field], "count": r["count"]}
                for r in rows
            ],
        })


class RiskSummaryView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(parameters=FILTER_PARAMS, responses=OpenApiTypes.OBJECT)
    def get(self, request):
        hp = filtered_structures(request).filter(type__code="hydropost")
        flood = {"critical": 0, "high": 0, "watch": 0, "none": 0}
        low_water = {"critical": 0, "high": 0, "watch": 0, "none": 0}
        forecast_crossing = 0
        assessments = ConditionAssessment.objects.filter(structure__in=hp)
        for a in assessments.iterator(chunk_size=500):
            risk = (a.risk_scores or {}).get("risk") or {}
            det = risk.get("detectors") or {}
            if not det:
                continue
            flood[det["flood"]["level"]] = flood.get(det["flood"]["level"], 0) + 1
            low_water[det["low_water"]["level"]] = low_water.get(det["low_water"]["level"], 0) + 1
            if det["forecast"].get("crosses_danger"):
                forecast_crossing += 1
        return Response({
            "flood": flood,
            "low_water": low_water,
            "forecast_crossing": forecast_crossing,
            "hydroposts": hp.count(),
        })


class LevelTimeseriesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[*FILTER_PARAMS, OpenApiParameter("days", int)],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        try:
            days = int(request.GET.get("days", 90))
        except ValueError:
            days = 90
        hp = filtered_structures(request).filter(type__code="hydropost")
        since = timezone.now() - timedelta(days=days)
        rows = (
            HydropostReading.objects.filter(structure__in=hp, ts__gte=since)
            .annotate(day=TruncDate("ts"))
            .values("day")
            .annotate(avg_level=Avg("water_level"))
            .order_by("day")
        )
        return Response([
            {"date": r["day"], "avg_level": round(r["avg_level"], 2) if r["avg_level"] else None}
            for r in rows
        ])
