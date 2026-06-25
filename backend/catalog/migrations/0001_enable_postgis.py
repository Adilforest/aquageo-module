from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Ensure the PostGIS extension exists before any geometry columns.

    Uses CREATE EXTENSION IF NOT EXISTS, so it is safe even when the database
    image already provisioned PostGIS.
    """

    initial = True

    dependencies = []

    operations = [
        CreateExtension("postgis"),
    ]
