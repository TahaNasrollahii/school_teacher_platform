from django.db import models
from django.utils.translation import gettext_lazy as _
from teachers.models import Teacher
from schools.models import School, SubjectNeed


class MatchStatus(models.TextChoices):
    """
    Lifecycle states of a teacher–school match.

    The status advances toward MUTUAL when both parties express interest.
    """
    PENDING = 'pending', _('Pending')
    SCHOOL_INTERESTED = 'school_interested', _('School interested')
    TEACHER_INTERESTED = 'teacher_interested', _('Teacher interested')
    MUTUAL = 'mutual', _('Mutual agreement')
    REJECTED = 'rejected', _('Rejected')


class TeacherSchoolMatch(models.Model):
    """
    Records the compatibility score between one teacher and one subject need.

    Score breakdown fields (salary_overlap_score, district_match, etc.) are
    stored alongside the aggregate match_score so that clients can display
    a transparent explanation of *why* a match was suggested.
    """

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name=_('Teacher'),
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name=_('School'),
    )
    subject_need = models.ForeignKey(
        SubjectNeed,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name=_('Subject need'),
    )

    # --- Score components ---
    match_score = models.FloatField(default=0.0, verbose_name=_('Overall match score'))
    salary_overlap_score = models.FloatField(
        default=0.0,
        verbose_name=_('Salary overlap score'),
    )
    district_match = models.BooleanField(
        default=False,
        verbose_name=_('Same district'),
    )
    subject_match = models.BooleanField(
        default=False,
        verbose_name=_('Subject match'),
    )
    level_match = models.BooleanField(
        default=False,
        verbose_name=_('Education level match'),
    )

    # --- Workflow ---
    status = models.CharField(
        max_length=20,
        choices=MatchStatus.choices,
        default=MatchStatus.PENDING,
        verbose_name=_('Status'),
    )
    school_note = models.TextField(blank=True, verbose_name=_('School note'))
    teacher_note = models.TextField(blank=True, verbose_name=_('Teacher note'))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    class Meta:
        verbose_name = _('Teacher–School match')
        verbose_name_plural = _('Teacher–School matches')
        # One match record per teacher–vacancy pair
        unique_together = ('teacher', 'subject_need')
        ordering = ['-match_score']

    def __str__(self) -> str:
        return (
            f"{self.teacher.full_name} ↔ {self.school.name} "
            f"[{self.match_score:.1f}%]"
        )
