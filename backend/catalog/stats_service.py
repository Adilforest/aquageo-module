"""Reusable dashboard aggregates (issue #20).

The stats API views (:mod:`catalog.stats_views`) and the report export endpoints
(:mod:`reports`, issue #31) both call these helpers, so the dashboard, the map and
the exported PDF/Excel always show the same numbers. Calculations live here and are
not duplicated per consumer. Aggregation is done in the DB, not on the client.
"""
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from assessment.models import ConditionAssessment
from monitoring.models import HydropostReading

from .filters import StructureFilter
from .models import ConditionStatus, Structure

CONDITIONS = [c.value for c in ConditionStatus]


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


def by_type(qs):
    """Count structures per ObjectType, busiest first."""
    rows = (
        qs.values("type_id", "type__name_ru")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return [
        {"type": r["type_id"], "type_name": r["type__name_ru"], "count": r["count"]}
        for r in rows
    ]


def by_condition(qs):
    """Distribution over condition_status plus total and a health index (0..100)."""
    counts = {c: 0 for c in CONDITIONS}
    for row in qs.values("condition_status").annotate(n=Count("id")):
        if row["condition_status"] in counts:
            counts[row["condition_status"]] = row["n"]
    total = sum(counts.values())
    healthy = counts["serviceable"] + counts["monitoring"]
    index = round(100 * healthy / total) if total else 0
    return {"counts": counts, "total": total, "index": index}


def by_territory(qs, group="basin"):
    """Count structures grouped by basin (default) or district."""
    if group == "district":
        id_field, name_field = "admin_unit_id", "admin_unit__name_ru"
    else:
        group = "basin"
        id_field, name_field = "basin_id", "basin__name_ru"
    rows = (
        qs.filter(**{f"{id_field}__isnull": False})
        .values(id_field, name_field)
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return {
        "group": group,
        "items": [
            {"id": str(r[id_field]), "name": r[name_field], "count": r["count"]}
            for r in rows
        ],
    }


def risk_summary(qs):
    """Flood / low-water / forecast risk levels across hydroposts in the queryset."""
    hp = qs.filter(type__code="hydropost")
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
    return {
        "flood": flood,
        "low_water": low_water,
        "forecast_crossing": forecast_crossing,
        "hydroposts": hp.count(),
    }


def level_timeseries(qs, days=90):
    """Daily average water level for hydroposts in the queryset over ``days``."""
    from datetime import timedelta

    hp = qs.filter(type__code="hydropost")
    since = timezone.now() - timedelta(days=days)
    rows = (
        HydropostReading.objects.filter(structure__in=hp, ts__gte=since)
        .annotate(day=TruncDate("ts"))
        .values("day")
        .annotate(avg_level=Avg("water_level"))
        .order_by("day")
    )
    return [
        {"date": r["day"], "avg_level": round(r["avg_level"], 2) if r["avg_level"] else None}
        for r in rows
    ]
