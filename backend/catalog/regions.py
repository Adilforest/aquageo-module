"""Region (top-level AdminUnit) helpers — scaling mechanism (#33).

A structure's ``admin_unit`` may sit at any KATO level (region/district/okrug).
Filtering "by region" therefore means matching the region itself plus all of its
descendant districts and okrugs. This logic is shared by the ``region`` filter
and the regions-list endpoint so the numbers stay consistent.
"""


def region_descendant_katos(region_kato):
    """Return [region, ...districts, ...okrugs] KATO codes under ``region_kato``."""
    from .models import AdminUnit

    districts = list(
        AdminUnit.objects.filter(parent_id=region_kato).values_list("kato", flat=True)
    )
    okrugs = list(
        AdminUnit.objects.filter(parent_id__in=districts).values_list("kato", flat=True)
    )
    return [region_kato, *districts, *okrugs]
