from django.contrib import admin
from django.contrib.gis import admin as gis_admin

from .models import AdminUnit, Basin, ObjectType, WaterBody


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
