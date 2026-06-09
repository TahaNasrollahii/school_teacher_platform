from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import TeacherSchoolMatch


@admin.register(TeacherSchoolMatch)
class TeacherSchoolMatchAdmin(ModelAdmin):
    """Admin view for TeacherSchoolMatch records."""

    list_display = [
        'teacher', 'school', 'subject_need',
        'match_score', 'status',
        'district_match', 'subject_match', 'level_match',
    ]
    list_filter = ['status', 'district_match', 'subject_match', 'level_match']
    search_fields = [
        'teacher__first_name', 'teacher__last_name', 'school__name',
    ]
    ordering = ['-match_score']
    readonly_fields = [
        'match_score', 'salary_overlap_score',
        'district_match', 'subject_match', 'level_match',
        'created_at', 'updated_at',
    ]

    fieldsets = [
        (_('Participants'), {
            'fields': ['teacher', 'school', 'subject_need'],
        }),
        (_('Score breakdown'), {
            'fields': [
                'match_score', 'salary_overlap_score',
                'district_match', 'subject_match', 'level_match',
            ],
        }),
        (_('Workflow'), {
            'fields': ['status', 'school_note', 'teacher_note'],
        }),
        (_('Timestamps'), {
            'fields': ['created_at', 'updated_at'],
        }),
    ]
