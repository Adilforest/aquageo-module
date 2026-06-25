from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Роль (RBAC)", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Роль (RBAC)", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff", "is_superuser")
    list_filter = (*UserAdmin.list_filter, "role")
