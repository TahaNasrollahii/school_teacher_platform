from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import School, SubjectNeed, SchoolType, EducationLevel


class SubjectNeedSerializer(serializers.ModelSerializer):
    """Serializer for a single subject vacancy."""

    class Meta:
        model = SubjectNeed
        fields = [
            'id', 'subject_name', 'education_level',
            'min_salary_per_hour', 'max_salary_per_hour',
            'is_filled', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data: dict) -> dict:
        """
        Ensure the salary range is logically ordered.

        Uses the existing instance values as fallbacks so that partial
        PATCH requests (e.g. sending only ``is_filled``) do not raise a
        KeyError when salary fields are absent from the payload.
        """
        instance = self.instance  # None on create, set on update
        min_salary = data.get(
            'min_salary_per_hour',
            getattr(instance, 'min_salary_per_hour', None),
        )
        max_salary = data.get(
            'max_salary_per_hour',
            getattr(instance, 'max_salary_per_hour', None),
        )
        if min_salary is not None and max_salary is not None:
            if min_salary > max_salary:
                raise serializers.ValidationError(
                    _('Minimum salary cannot exceed maximum salary.')
                )
        return data


class SchoolSerializer(serializers.ModelSerializer):
    """Read serializer for a full school profile including its subject needs."""

    subject_needs = SubjectNeedSerializer(many=True, read_only=True)

    class Meta:
        model = School
        fields = [
            'id', 'name', 'school_type', 'education_level',
            'phone', 'district', 'address',
            'subject_needs', 'is_verified', 'created_at',
        ]
        read_only_fields = ['id', 'is_verified', 'created_at']


class SchoolRegistrationSerializer(serializers.Serializer):
    """
    Compound serializer used only for the registration endpoint.

    Creates a User, a School, and one-or-more SubjectNeed records
    inside a single validated payload.
    """

    # User credentials
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=False, allow_blank=True)

    # School profile
    name = serializers.CharField(max_length=200)
    school_type = serializers.ChoiceField(choices=SchoolType.choices)
    education_level = serializers.ChoiceField(choices=EducationLevel.choices)
    phone = serializers.CharField(max_length=15)
    district = serializers.CharField(max_length=100)
    address = serializers.CharField()
    subject_needs = SubjectNeedSerializer(many=True)

    def validate_username(self, value: str) -> str:
        """Reject duplicate usernames early with a clear message."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                _('This username is already taken.')
            )
        return value

    def validate_subject_needs(self, value: list) -> list:
        """At least one subject need must be supplied."""
        if not value:
            raise serializers.ValidationError(
                _('At least one subject need is required.')
            )
        return value

    def create(self, validated_data: dict) -> School:
        """
        Atomically create the User, School, and all SubjectNeed records.

        Called only after full validation passes.
        """
        subject_needs_data = validated_data.pop('subject_needs')
        user = User.objects.create_user(
            username=validated_data.pop('username'),
            password=validated_data.pop('password'),
            email=validated_data.pop('email', ''),
        )
        school = School.objects.create(user=user, **validated_data)
        for need_data in subject_needs_data:
            SubjectNeed.objects.create(school=school, **need_data)
        return school


class SchoolLoginSerializer(serializers.Serializer):
    """Credentials payload for the school login endpoint."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
