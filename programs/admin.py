from django.contrib import admin

from programs.models import CurriculumItem, Program


class CurriculumItemInline(admin.TabularInline):
    model = CurriculumItem
    extra = 0
    ordering = ["period"]


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_published"]
    list_filter = ["is_published"]
    inlines = [CurriculumItemInline]
