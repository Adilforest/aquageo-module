"""Compare a parsed draft against the catalog (issue #23, ТЗ task 4).

Rules:
- close by coordinates (<= 300 m) AND similar name AND same type -> existing
- only one of (geo / name) matches -> needs_check
- nothing close -> new
Fills ParseJob.match_status / matched_structure.
"""
from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

from django.contrib.gis.geos import Polygon

from catalog.models import Structure

from .models import ParseJob

GEO_THRESHOLD_M = 300
NAME_THRESHOLD = 0.6


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _norm(s: str | None) -> str:
    return re.sub(r"[^\w\s]", "", (s or "").lower()).strip()


def name_similarity(a: str | None, b: str | None) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _candidate_qs(draft):
    qs = Structure.objects.exclude(origin_parse_jobs__isnull=False)
    if draft.pk:
        qs = qs.exclude(pk=draft.pk)
    return qs


def _nearby(draft) -> list:
    if draft.geom is None:
        return []
    x, y = draft.geom.x, draft.geom.y
    d = 0.006  # ~600 m bbox prefilter; exact distance checked below
    bbox = Polygon.from_bbox((x - d, y - d, x + d, y + d))
    bbox.srid = 4326
    found = []
    for s in _candidate_qs(draft).filter(geom__isnull=False, geom__within=bbox):
        dist = _haversine_m(y, x, s.geom.y, s.geom.x)
        if dist <= GEO_THRESHOLD_M:
            found.append((dist, s))
    found.sort(key=lambda t: t[0])
    return [s for _, s in found]


def compute_match(draft):
    """Return (match_status, matched_structure) for a draft Structure."""
    if draft is None:
        return ParseJob.MatchStatus.NEW, None

    geo_close = _nearby(draft)
    existing = next(
        (s for s in geo_close
         if s.type_id == draft.type_id
         and name_similarity(draft.name_ru, s.name_ru) >= NAME_THRESHOLD),
        None,
    )
    if existing:
        return ParseJob.MatchStatus.EXISTING, existing

    # only-name match anywhere (same type)
    name_match = None
    for s in _candidate_qs(draft).filter(type_id=draft.type_id).iterator(chunk_size=500):
        if name_similarity(draft.name_ru, s.name_ru) >= NAME_THRESHOLD:
            name_match = s
            break

    if geo_close or name_match:
        return ParseJob.MatchStatus.NEEDS_CHECK, (geo_close[0] if geo_close else name_match)
    return ParseJob.MatchStatus.NEW, None


def match_parse_job(job):
    """Compute and persist match_status / matched_structure for a ParseJob."""
    status, matched = compute_match(job.result_structure)
    job.match_status = status
    job.matched_structure = matched
    job.save(update_fields=["match_status", "matched_structure", "updated_at"])
    return status, matched
