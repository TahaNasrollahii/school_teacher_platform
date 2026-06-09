from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline

from .models import School, SubjectNeed


class SubjectNeedInline(TabularInline):
    """Inline editor for subject needs inside the school admin page."""

    model = SubjectNeed
    extra = 0
    fields = [
        'subject_name', 'education_level',
        'min_salary_per_hour', 'max_salary_per_hour', 'is_filled',
    ]
    show_change_link = True


@admin.register(School)
class SchoolAdmin(ModelAdmin):
    """Admin view for School records."""

    list_display = [
        'name', 'school_type', 'education_level',
        'district', 'phone', 'is_verified',
    ]
    list_filter = ['school_type', 'education_level', 'district', 'is_verified']
    search_fields = ['name', 'district', 'phone']
    list_editable = ['is_verified']
    inlines = [SubjectNeedInline]

    # Unfold fieldset layout
    fieldsets = [
        (_('Basic information'), {
            'fields': ['user', 'name', 'school_type', 'education_level'],
        }),
        (_('Contact & location'), {
            'fields': ['phone', 'district', 'address'],
        }),
        (_('Status'), {
            'fields': ['is_verified'],
        }),
    ]


@admin.register(SubjectNeed)
class SubjectNeedAdmin(ModelAdmin):
    """Admin view for SubjectNeed records."""

    list_display = [
        'school', 'subject_name', 'education_level',
        'min_salary_per_hour', 'max_salary_per_hour', 'is_filled',
    ]
    list_filter = ['education_level', 'is_filled']
    search_fields = ['subject_name', 'school__name']
    list_editable = ['is_filled']

    fieldsets = [
        (_('Vacancy details'), {
            'fields': ['school', 'subject_name', 'education_level'],
        }),
        (_('Salary range (Toman / hour)'), {
            'fields': ['min_salary_per_hour', 'max_salary_per_hour'],
        }),
        (_('Status'), {
            'fields': ['is_filled'],
        }),
    ]
