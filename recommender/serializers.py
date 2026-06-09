from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import TeacherSchoolMatch, MatchStatus


class MatchSerializer(serializers.ModelSerializer):
    """
    Read serializer for a TeacherSchoolMatch record.

    Includes denormalised fields (names, salary ranges, district) so
    clients need only a single request to render a complete match card.
    """

    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    subject_name = serializers.CharField(source='subject_need.subject_name', read_only=True)
    teacher_district = serializers.CharField(source='teacher.district', read_only=True)
    school_district = serializers.CharField(source='school.district', read_only=True)
    teacher_salary_range = serializers.SerializerMethodField()
    school_salary_range = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TeacherSchoolMatch
        fields = [
            'id', 'teacher_name', 'school_name', 'subject_name',
            'match_score', 'salary_overlap_score',
            'district_match', 'subject_match', 'level_match',
            'status', 'status_display',
            'teacher_district', 'school_district',
            'teacher_salary_range', 'school_salary_range',
            'school_note', 'teacher_note',
            'created_at',
        ]

    def get_teacher_salary_range(self, obj) -> dict:
        """Return the teacher's acceptable hourly salary range."""
        return {
            'min': obj.teacher.min_salary_per_hour,
            'max': obj.teacher.max_salary_per_hour,
        }

    def get_school_salary_range(self, obj) -> dict:
        """Return the school's budgeted hourly salary range for this vacancy."""
        return {
            'min': obj.subject_need.min_salary_per_hour,
            'max': obj.subject_need.max_salary_per_hour,
        }


class MatchStatusUpdateSerializer(serializers.Serializer):
    """Payload for updating the workflow status of a match."""

    status = serializers.ChoiceField(choices=MatchStatus.choices)
    note = serializers.CharField(required=False, allow_blank=True)
