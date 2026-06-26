import django_filters as df
from django import forms

from .models import Structure


class _AnyMultipleChoiceField(forms.MultipleChoiceField):
    """MultipleChoiceField that accepts arbitrary values (no choice list)."""

    def valid_value(self, value):
        return True


class MultiValueFilter(df.MultipleChoiceFilter):
    """Repeated query params become an OR (field__in) filter.

    e.g. ?condition=repair&condition=emergency. Unknown values match nothing.
    """

    field_class = _AnyMultipleChoiceField


class StructureFilter(df.FilterSet):
    """Filters for /api/v1/structures and the GeoJSON feed.

    Primary (multi-select): ``type``, ``condition``. Secondary (single):
    ``basin``, ``district``. Free-text search is handled by SearchFilter.
    """

    type = MultiValueFilter(field_name="type__code")
    condition = MultiValueFilter(field_name="condition_status")
    basin = df.UUIDFilter(field_name="basin_id")
    district = df.CharFilter(field_name="admin_unit_id")
    needs_geocoding = df.BooleanFilter(field_name="needs_geocoding")

    # Backwards-compatible single-value aliases (used by KPI counters, #14).
    condition_status = df.CharFilter(field_name="condition_status")
    admin_unit = df.CharFilter(field_name="admin_unit_id")
    status = df.CharFilter()
    significance = df.CharFilter()

    class Meta:
        model = Structure
        fields = [
            "type", "condition", "basin", "district", "needs_geocoding",
            "condition_status", "admin_unit", "status", "significance",
        ]
