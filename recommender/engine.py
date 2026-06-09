"""
Recommendation engine for the School-Teacher Matching Platform.

Scoring algorithm (max 100 points + bonuses):
  - District match         : 35 pts  (teacher and school in the same district)
  - Salary overlap         : up to 40 pts  (proportional to range intersection)
  - Subject match          : 15 pts  (teacher teaches the required subject)
  - Education level match  : 10 pts  (teacher's primary level == school's need)
  - Experience bonus       : up to 5 pts  (0.5 pt per year of experience)
  - Publications bonus     : up to 3 pts  (0.5 pt per publication line)

Only matches at or above ``min_score`` are persisted to the database.
"""

from teachers.models import Teacher, TeachingSubject
from schools.models import School, SubjectNeed
from .models import TeacherSchoolMatch


# ---------------------------------------------------------------------------
# Salary overlap helper
# ---------------------------------------------------------------------------

def calculate_salary_overlap(
    t_min: int, t_max: int, s_min: int, s_max: int
) -> float:
    """
    Compute the fractional overlap between two salary ranges [t_min, t_max]
    and [s_min, s_max].

    Returns a value in [0, 1]:
      - 1.0  → the smaller range is fully contained in the other
      - 0.0  → no overlap and the gap is large relative to both ranges
      - 0..0.3 → no overlap but the gap is small (partial credit)

    Parameters
    ----------
    t_min, t_max : int
        Teacher's acceptable hourly salary range.
    s_min, s_max : int
        School's budgeted hourly salary range.
    """
    overlap_start = max(t_min, s_min)
    overlap_end = min(t_max, s_max)

    if overlap_start > overlap_end:
        # No overlap – award partial credit proportional to proximity
        gap = overlap_start - overlap_end
        avg_range = ((t_max - t_min) + (s_max - s_min)) / 2
        if avg_range == 0:
            return 0.0
        penalty = min(gap / avg_range, 1.0)
        return max(0.0, 0.3 * (1 - penalty))

    overlap_length = overlap_end - overlap_start
    teacher_range = max(t_max - t_min, 1)
    school_range = max(s_max - s_min, 1)
    smaller_range = min(teacher_range, school_range)

    return min(overlap_length / smaller_range, 1.0)


# ---------------------------------------------------------------------------
# Per-pair scoring
# ---------------------------------------------------------------------------

def calculate_match_score(teacher: Teacher, subject_need: SubjectNeed) -> dict:
    """
    Compute the full compatibility score between *teacher* and *subject_need*.

    Returns a dictionary with individual component scores and a
    ``total_score`` key capped at 100.

    Parameters
    ----------
    teacher : Teacher
        The candidate teacher.
    subject_need : SubjectNeed
        The vacancy being evaluated.
    """
    school = subject_need.school
    score = 0.0
    details: dict = {}

    # 1. District match (35 pts)
    district_match = teacher.district.strip() == school.district.strip()
    if district_match:
        score += 35
    details['district_match'] = district_match

    # 2. Salary overlap (up to 40 pts)
    salary_overlap = calculate_salary_overlap(
        teacher.min_salary_per_hour, teacher.max_salary_per_hour,
        subject_need.min_salary_per_hour, subject_need.max_salary_per_hour,
    )
    salary_score = salary_overlap * 40
    score += salary_score
    details['salary_overlap_score'] = salary_score
    details['salary_overlap_pct'] = round(salary_overlap * 100, 1)

    # 3. Subject match (15 pts)
    subject_match = teacher.subjects.filter(
        subject_name__iexact=subject_need.subject_name
    ).exists()
    if subject_match:
        score += 15
    details['subject_match'] = subject_match

    # 4. Education level match (10 pts, 5 pts partial)
    level_match = teacher.education_level == subject_need.education_level
    if level_match:
        score += 10
    elif teacher.subjects.filter(education_level=subject_need.education_level).exists():
        # Teacher has taught at the required level in some other subject
        score += 5
    details['level_match'] = level_match

    # 5. Experience bonus (up to 5 pts)
    exp_bonus = min(teacher.experience_years * 0.5, 5)
    score += exp_bonus
    details['experience_bonus'] = exp_bonus

    # 6. Publications bonus (up to 3 pts)
    if teacher.publications.strip():
        pub_count = len([p for p in teacher.publications.split('\n') if p.strip()])
        pub_bonus = min(pub_count * 0.5, 3)
    else:
        pub_bonus = 0.0
    score += pub_bonus
    details['publications_bonus'] = pub_bonus

    details['total_score'] = round(min(score, 100), 2)
    return details


# ---------------------------------------------------------------------------
# Bulk engine
# ---------------------------------------------------------------------------

def run_recommendation_engine(min_score: float = 30.0) -> dict:
    """
    Run the full recommendation engine across all available teachers and
    unfilled subject needs.

    For each (teacher, subject_need) pair whose score meets *min_score*,
    a TeacherSchoolMatch record is created or updated.

    Parameters
    ----------
    min_score : float
        Pairs scoring below this threshold are skipped (default 30.0).

    Returns
    -------
    dict
        ``{'created': int, 'updated': int}`` counts.
    """
    teachers = Teacher.objects.filter(is_available=True).prefetch_related('subjects')
    subject_needs = SubjectNeed.objects.filter(is_filled=False).select_related('school')

    created_count = 0
    updated_count = 0

    for need in subject_needs:
        for teacher in teachers:
            score_details = calculate_match_score(teacher, need)
            total_score = score_details['total_score']

            if total_score < min_score:
                continue  # Skip poor matches

            _, created = TeacherSchoolMatch.objects.update_or_create(
                teacher=teacher,
                subject_need=need,
                defaults={
                    'school': need.school,
                    'match_score': total_score,
                    'salary_overlap_score': score_details['salary_overlap_score'],
                    'district_match': score_details['district_match'],
                    'subject_match': score_details['subject_match'],
                    'level_match': score_details['level_match'],
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

    return {'created': created_count, 'updated': updated_count}


# ---------------------------------------------------------------------------
# Per-user query helpers
# ---------------------------------------------------------------------------

def get_matches_for_school(school: School, min_score: float = 30.0):
    """
    Return all TeacherSchoolMatch records for *school* ordered by score.

    Parameters
    ----------
    school : School
    min_score : float
        Only return matches at or above this score.
    """
    return (
        TeacherSchoolMatch.objects
        .filter(school=school, match_score__gte=min_score)
        .select_related('teacher', 'subject_need')
        .order_by('-match_score')
    )


def get_matches_for_teacher(teacher: Teacher, min_score: float = 30.0):
    """
    Return all TeacherSchoolMatch records for *teacher* ordered by score.

    Parameters
    ----------
    teacher : Teacher
    min_score : float
        Only return matches at or above this score.
    """
    return (
        TeacherSchoolMatch.objects
        .filter(teacher=teacher, match_score__gte=min_score)
        .select_related('school', 'subject_need')
        .order_by('-match_score')
    )
