import django_filters as df

from .models import Structure


class StructureFilter(df.FilterSet):
    """Filters for /api/v1/structures: by type, condition, basin, district."""

    type = df.CharFilter(field_name="type__code")
    basin = df.UUIDFilter(field_name="basin_id")
    admin_unit = df.CharFilter(field_name="admin_unit_id")
    condition_status = df.CharFilter()
    status = df.CharFilter()
    significance = df.CharFilter()

    class Meta:
        model = Structure
        fields = ["type", "basin", "admin_unit", "condition_status", "status", "significance"]
