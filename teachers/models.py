from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from schools.models import EducationLevel


class Teacher(models.Model):
    """
    Represents a registered teacher.

    Linked 1-to-1 with a Django User account.  Teaching subjects are
    stored as separate TeachingSubject records so one teacher can
    cover multiple subjects and levels.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name=_('User account'),
    )
    first_name = models.CharField(max_length=100, verbose_name=_('First name'))
    last_name = models.CharField(max_length=100, verbose_name=_('Last name'))
    national_id = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_('National ID'),
    )
    phone = models.CharField(max_length=15, verbose_name=_('Phone number'))
    education_level = models.CharField(
        max_length=10,
        choices=EducationLevel.choices,
        verbose_name=_('Primary teaching level'),
    )
    district = models.CharField(max_length=100, verbose_name=_('District'))
    experience_years = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Years of experience'),
    )
    schools_history = models.TextField(
        blank=True,
        verbose_name=_('Previous schools and institutes'),
    )
    publications = models.TextField(
        blank=True,
        verbose_name=_('Publications and authored materials'),
    )
    min_salary_per_hour = models.PositiveIntegerField(
        verbose_name=_('Minimum expected salary per hour (Toman)'),
    )
    max_salary_per_hour = models.PositiveIntegerField(
        verbose_name=_('Maximum expected salary per hour (Toman)'),
    )
    bio = models.TextField(blank=True, verbose_name=_('Biography'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))
    is_available = models.BooleanField(default=True, verbose_name=_('Available for hire'))

    class Meta:
        verbose_name = _('Teacher')
        verbose_name_plural = _('Teachers')
        ordering = ['last_name', 'first_name']

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} – {_('District')} {self.district}"

    @property
    def full_name(self) -> str:
        """Return the teacher's full display name."""
        return f"{self.first_name} {self.last_name}"


class TeachingSubject(models.Model):
    """
    A subject/level pair that a teacher is qualified to teach.

    The combination of (teacher, subject_name, education_level) is
    enforced as unique so there are no duplicate records.
    """

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name=_('Teacher'),
    )
    subject_name = models.CharField(max_length=100, verbose_name=_('Subject name'))
    education_level = models.CharField(
        max_length=10,
        choices=EducationLevel.choices,
        verbose_name=_('Education level'),
    )
    years_of_experience = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Years of experience in this subject'),
    )

    class Meta:
        verbose_name = _('Teaching subject')
        verbose_name_plural = _('Teaching subjects')
        unique_together = ('teacher', 'subject_name', 'education_level')
        ordering = ['subject_name']

    def __str__(self) -> str:
        return f"{self.teacher.full_name} – {self.subject_name}"
