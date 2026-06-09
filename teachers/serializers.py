from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import Teacher, TeachingSubject
from schools.models import EducationLevel


class TeachingSubjectSerializer(serializers.ModelSerializer):
    """Serializer for a single subject/level taught by a teacher."""

    class Meta:
        model = TeachingSubject
        fields = ['id', 'subject_name', 'education_level', 'years_of_experience']
        read_only_fields = ['id']


class TeacherSerializer(serializers.ModelSerializer):
    """Read serializer for a full teacher profile including subjects."""

    subjects = TeachingSubjectSerializer(many=True, read_only=True)
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Teacher
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'national_id', 'phone', 'education_level', 'district',
            'experience_years', 'schools_history', 'publications',
            'min_salary_per_hour', 'max_salary_per_hour',
            'bio', 'is_available', 'subjects', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class TeacherRegistrationSerializer(serializers.Serializer):
    """
    Compound serializer for teacher registration.

    Creates a User, a Teacher, and one-or-more TeachingSubject records
    in a single atomic request.
    """

    # User credentials
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=False, allow_blank=True)

    # Teacher profile
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    national_id = serializers.CharField(max_length=10, min_length=10)
    phone = serializers.CharField(max_length=15)
    education_level = serializers.ChoiceField(choices=EducationLevel.choices)
    district = serializers.CharField(max_length=100)
    experience_years = serializers.IntegerField(min_value=0)
    schools_history = serializers.CharField(required=False, allow_blank=True, default='')
    publications = serializers.CharField(required=False, allow_blank=True, default='')
    min_salary_per_hour = serializers.IntegerField(min_value=0)
    max_salary_per_hour = serializers.IntegerField(min_value=0)
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    subjects = TeachingSubjectSerializer(many=True)

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(_('This username is already taken.'))
        return value

    def validate_national_id(self, value: str) -> str:
        """National ID must be exactly 10 digits and globally unique."""
        if not value.isdigit():
            raise serializers.ValidationError(
                _('National ID must contain digits only.')
            )
        if Teacher.objects.filter(national_id=value).exists():
            raise serializers.ValidationError(
                _('A teacher with this national ID is already registered.')
            )
        return value

    def validate(self, data: dict) -> dict:
        if data['min_salary_per_hour'] > data['max_salary_per_hour']:
            raise serializers.ValidationError(
                _('Minimum salary cannot exceed maximum salary.')
            )
        if not data.get('subjects'):
            raise serializers.ValidationError(
                _('At least one teaching subject is required.')
            )
        return data

    def create(self, validated_data: dict) -> Teacher:
        """Atomically create the User, Teacher, and all TeachingSubject records."""
        subjects_data = validated_data.pop('subjects')
        user = User.objects.create_user(
            username=validated_data.pop('username'),
            password=validated_data.pop('password'),
            email=validated_data.pop('email', ''),
        )
        teacher = Teacher.objects.create(user=user, **validated_data)
        for subject_data in subjects_data:
            TeachingSubject.objects.create(teacher=teacher, **subject_data)
        return teacher
