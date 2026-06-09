from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline

from .models import Teacher, TeachingSubject


class TeachingSubjectInline(TabularInline):
    """Inline editor for teaching subjects inside the teacher admin page."""

    model = TeachingSubject
    extra = 0
    fields = ['subject_name', 'education_level', 'years_of_experience']
    show_change_link = True


@admin.register(Teacher)
class TeacherAdmin(ModelAdmin):
    """Admin view for Teacher records."""

    list_display = [
        'full_name', 'national_id', 'education_level',
        'district', 'experience_years', 'is_available',
    ]
    list_filter = ['education_level', 'district', 'is_available']
    search_fields = ['first_name', 'last_name', 'national_id', 'phone']
    list_editable = ['is_available']
    inlines = [TeachingSubjectInline]

    fieldsets = [
        (_('Personal information'), {
            'fields': [
                'user', 'first_name', 'last_name',
                'national_id', 'phone',
            ],
        }),
        (_('Teaching profile'), {
            'fields': [
                'education_level', 'district',
                'experience_years', 'schools_history', 'publications',
            ],
        }),
        (_('Salary expectations (Toman / hour)'), {
            'fields': ['min_salary_per_hour', 'max_salary_per_hour'],
        }),
        (_('Additional'), {
            'fields': ['bio', 'is_available'],
        }),
    ]


@admin.register(TeachingSubject)
class TeachingSubjectAdmin(ModelAdmin):
    """Admin view for TeachingSubject records."""

    list_display = [
        'teacher', 'subject_name',
        'education_level', 'years_of_experience',
    ]
    list_filter = ['education_level']
    search_fields = [
        'subject_name',
        'teacher__first_name', 'teacher__last_name',
    ]

    fieldsets = [
        (_('Subject details'), {
            'fields': [
                'teacher', 'subject_name',
                'education_level', 'years_of_experience',
            ],
        }),
    ]
