from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class SchoolType(models.TextChoices):
    """Gender policy of the school."""
    GIRLS = 'girls', _('Girls')
    BOYS = 'boys', _('Boys')
    MIXED = 'mixed', _('Mixed')


class EducationLevel(models.TextChoices):
    """Iranian education levels."""
    PRIMARY = 'primary', _('Primary')
    MIDDLE = 'middle', _('Middle School')
    HIGH = 'high', _('High School')


class School(models.Model):
    """
    Represents a registered school institution.

    Each school is linked to exactly one Django User account and can
    advertise multiple subject needs through SubjectNeed records.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='school_profile',
        verbose_name=_('User account'),
    )
    name = models.CharField(max_length=200, verbose_name=_('School name'))
    school_type = models.CharField(
        max_length=10,
        choices=SchoolType.choices,
        verbose_name=_('School type'),
    )
    education_level = models.CharField(
        max_length=10,
        choices=EducationLevel.choices,
        verbose_name=_('Education level'),
    )
    phone = models.CharField(max_length=15, verbose_name=_('Phone number'))
    district = models.CharField(max_length=100, verbose_name=_('District'))
    address = models.TextField(verbose_name=_('Address'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))
    is_verified = models.BooleanField(default=False, verbose_name=_('Verified'))

    class Meta:
        verbose_name = _('School')
        verbose_name_plural = _('Schools')
        ordering = ['name']

    def __str__(self) -> str:
        return f"{self.name} – {_('District')} {self.district}"


class SubjectNeed(models.Model):
    """
    A single teaching vacancy advertised by a school.

    Stores the subject name, required education level, and the
    acceptable hourly salary range.  When a teacher fills the role,
    ``is_filled`` should be set to True.
    """

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='subject_needs',
        verbose_name=_('School'),
    )
    subject_name = models.CharField(max_length=100, verbose_name=_('Subject name'))
    education_level = models.CharField(
        max_length=10,
        choices=EducationLevel.choices,
        verbose_name=_('Required education level'),
    )
    min_salary_per_hour = models.PositiveIntegerField(
        verbose_name=_('Minimum salary per hour (Toman)'),
    )
    max_salary_per_hour = models.PositiveIntegerField(
        verbose_name=_('Maximum salary per hour (Toman)'),
    )
    is_filled = models.BooleanField(default=False, verbose_name=_('Position filled'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))

    class Meta:
        verbose_name = _('Subject need')
        verbose_name_plural = _('Subject needs')
        ordering = ['subject_name']

    def __str__(self) -> str:
        return (
            f"{self.school.name} – {self.subject_name} "
            f"({self.get_education_level_display()})"
        )
