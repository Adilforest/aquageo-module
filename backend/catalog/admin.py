from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from .models import (
    AdminUnit,
    Attachment,
    Basin,
    Inspection,
    ObjectType,
    Structure,
    WaterBody,
)


@admin.register(ObjectType)
class ObjectTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ru", "geometry_kind")
    search_fields = ("code", "name_ru", "name_kk", "name_en")


@admin.register(AdminUnit)
class AdminUnitAdmin(admin.ModelAdmin):
    list_display = ("kato", "name_ru", "level", "parent")
    list_filter = ("level",)
    search_fields = ("kato", "name_ru", "name_kk")
    autocomplete_fields = ("parent",)


@admin.register(Basin)
class BasinAdmin(gis_admin.GISModelAdmin):
    list_display = ("name_ru", "name_kk")
    search_fields = ("name_ru", "name_kk", "name_en")


@admin.register(WaterBody)
class WaterBodyAdmin(gis_admin.GISModelAdmin):
    list_display = ("name_ru", "kind", "basin")
    list_filter = ("kind",)
    search_fields = ("name_ru", "name_kk", "name_en")
    autocomplete_fields = ("basin",)


class InspectionInline(admin.TabularInline):
    model = Inspection
    extra = 0


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0


@admin.register(Structure)
class StructureAdmin(gis_admin.GISModelAdmin):
    list_display = (
        "name_ru",
        "type",
        "condition_status",
        "status",
        "significance",
        "basin",
        "admin_unit",
    )
    list_filter = ("type", "condition_status", "status", "significance")
    search_fields = ("name_ru", "name_kk", "name_en", "cadastral_number")
    autocomplete_fields = ("type", "water_body", "basin", "admin_unit")
    inlines = (InspectionInline, AttachmentInline)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("kind", "structure", "uploaded_by", "created_at")
    list_filter = ("kind",)


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = ("structure", "inspected_at", "inspector", "condition_observed")
    list_filter = ("condition_observed",)
    search_fields = ("inspector",)
    date_hierarchy = "inspected_at"
