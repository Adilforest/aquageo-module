"""Periodic recompute task (wired to celery beat; not required to run live)."""
from celery import shared_task


@shared_task
def recompute_assessments_task() -> int:
    """Recompute assessments (condition/repair/interval/risk) for all structures."""
    from assessment.services import save_assessment
    from catalog.models import Structure

    count = 0
    qs = Structure.objects.select_related("type").prefetch_related("inspections")
    for structure in qs.iterator(chunk_size=500):
        save_assessment(structure)
        count += 1
    return count
