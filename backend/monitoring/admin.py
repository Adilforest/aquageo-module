from django.contrib import admin

from .models import HydropostReading


@admin.register(HydropostReading)
class HydropostReadingAdmin(admin.ModelAdmin):
    list_display = ("structure", "ts", "water_level", "danger_level", "discharge", "synthetic")
    list_filter = ("synthetic", "status_code")
    search_fields = ("structure__name_ru",)
    date_hierarchy = "ts"
