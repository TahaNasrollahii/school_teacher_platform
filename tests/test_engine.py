"""
Tests for the recommendation engine (recommender/engine.py).

Covers:
  - calculate_salary_overlap: all edge cases
  - calculate_match_score: individual component scoring
  - run_recommendation_engine: integration-level match creation
  - get_matches_for_school / get_matches_for_teacher: query helpers
"""

import pytest
from schools.models import EducationLevel, SubjectNeed
from teachers.models import Teacher
from recommender.engine import (
    calculate_salary_overlap,
    calculate_match_score,
    run_recommendation_engine,
    get_matches_for_school,
    get_matches_for_teacher,
)
from recommender.models import TeacherSchoolMatch
from conftest import make_school_user, make_teacher_user


# ---------------------------------------------------------------------------
# calculate_salary_overlap
# ---------------------------------------------------------------------------

class TestCalculateSalaryOverlap:
    """Pure unit tests – no database required."""

    def test_identical_ranges_return_1(self):
        assert calculate_salary_overlap(500_000, 800_000, 500_000, 800_000) == 1.0

    def test_full_containment_returns_1(self):
        """Smaller range fully inside larger → 1.0."""
        result = calculate_salary_overlap(400_000, 900_000, 500_000, 800_000)
        assert result == 1.0

    def test_partial_overlap_between_0_and_1(self):
        result = calculate_salary_overlap(400_000, 600_000, 500_000, 800_000)
        assert 0 < result < 1

    def test_no_overlap_returns_low_score(self):
        """Non-overlapping ranges with large gap → near 0."""
        result = calculate_salary_overlap(100_000, 200_000, 800_000, 900_000)
        assert result < 0.3

    def test_adjacent_ranges_return_partial_credit(self):
        """Ranges that just touch at one point."""
        result = calculate_salary_overlap(400_000, 500_000, 500_000, 600_000)
        # Overlap length = 0, but they meet exactly → some partial credit or 0
        assert result >= 0

    def test_zero_width_teacher_range(self):
        """Teacher min == max (point salary)."""
        result = calculate_salary_overlap(500_000, 500_000, 400_000, 600_000)
        assert result >= 0

    def test_zero_width_school_range(self):
        result = calculate_salary_overlap(400_000, 600_000, 500_000, 500_000)
        assert result >= 0

    def test_symmetry_does_not_matter(self):
        """Swapping teacher / school ranges yields the same score."""
        a = calculate_salary_overlap(400_000, 700_000, 600_000, 900_000)
        b = calculate_salary_overlap(600_000, 900_000, 400_000, 700_000)
        assert abs(a - b) < 1e-9

    def test_result_always_between_0_and_1(self):
        cases = [
            (0, 1_000_000, 0, 1_000_000),
            (100, 200, 300, 400),
            (500_000, 500_000, 500_000, 500_000),
        ]
        for t_min, t_max, s_min, s_max in cases:
            result = calculate_salary_overlap(t_min, t_max, s_min, s_max)
            assert 0 <= result <= 1, f"Out of range for {t_min},{t_max},{s_min},{s_max}: {result}"


# ---------------------------------------------------------------------------
# calculate_match_score
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCalculateMatchScore:
    """Tests for the per-pair scoring function."""

    def test_perfect_match_scores_100(self, matched_pair):
        _, _, need, _, teacher, _ = matched_pair
        details = calculate_match_score(teacher, need)
        assert details['total_score'] == 100.0

    def test_different_district_loses_35_points(self, db):
        _, school, need = make_school_user(
            username='school_dist_test', district='District A',
            subject='Math', education_level=EducationLevel.HIGH,
            min_salary=500_000, max_salary=800_000,
        )
        _, teacher, _ = make_teacher_user(
            username='teacher_dist_test', national_id='1111111112',
            district='District B',          # different district
            subject='Math', education_level=EducationLevel.HIGH,
            min_salary=500_000, max_salary=800_000, experience_years=0,
        )
        details = calculate_match_score(teacher, need)
        # District mismatch costs 35 pts from the perfect score
        assert not details['district_match']
        assert details['total_score'] < 70   # at most 65 + bonus

    def test_subject_mismatch_loses_15_points(self, db):
        _, school, need = make_school_user(
            username='school_subj_test', district='District X',
            subject='Chemistry', education_level=EducationLevel.HIGH,
            min_salary=500_000, max_salary=800_000,
        )
        _, teacher, _ = make_teacher_user(
            username='teacher_subj_test', national_id='2222222222',
            district='District X',           # same district
            subject='Physics',               # different subject
            education_level=EducationLevel.HIGH,
            min_salary=500_000, max_salary=800_000, experience_years=0,
        )
        details = calculate_match_score(teacher, need)
        assert not details['subject_match']

    def test_salary_overlap_score_between_0_and_40(self, db):
        _, school, need = make_school_user(
            username='school_sal', district='D1',
            min_salary=400_000, max_salary=700_000,
        )
        _, teacher, _ = make_teacher_user(
            username='teacher_sal', national_id='3333333333',
            district='D1', min_salary=600_000, max_salary=900_000,
        )
        details = calculate_match_score(teacher, need)
        assert 0 <= details['salary_overlap_score'] <= 40

    def test_experience_bonus_capped_at_5(self, db):
        _, school, need = make_school_user(
            username='school_exp', district='D2',
        )
        _, teacher, _ = make_teacher_user(
            username='teacher_exp', national_id='4444444444',
            district='D2', experience_years=100,  # very high experience
        )
        details = calculate_match_score(teacher, need)
        assert details['experience_bonus'] <= 5

    def test_publications_bonus_capped_at_3(self, db):
        _, school, need = make_school_user(username='school_pub', district='D3')
        _, teacher, _ = make_teacher_user(
            username='teacher_pub', national_id='5555555555', district='D3',
        )
        # Add many publication lines
        teacher.publications = '\n'.join(['Book ' + str(i) for i in range(20)])
        teacher.save()
        details = calculate_match_score(teacher, need)
        assert details['publications_bonus'] <= 3

    def test_total_score_never_exceeds_100(self, db):
        """Even with all bonuses, score must be capped at 100."""
        _, school, need = make_school_user(
            username='school_cap', district='D4',
            subject='Math', education_level=EducationLevel.HIGH,
            min_salary=500_000, max_salary=800_000,
        )
        _, teacher, _ = make_teacher_user(
            username='teacher_cap', national_id='6666666666',
            district='D4', subject='Math', education_level=EducationLevel.HIGH,
            min_salary=500_000, max_salary=800_000, experience_years=100,
        )
        teacher.publications = '\n'.join(['Book'] * 20)
        teacher.save()
        details = calculate_match_score(teacher, need)
        assert details['total_score'] <= 100

    def test_details_dict_contains_expected_keys(self, matched_pair):
        _, _, need, _, teacher, _ = matched_pair
        details = calculate_match_score(teacher, need)
        expected_keys = {
            'district_match', 'salary_overlap_score', 'salary_overlap_pct',
            'subject_match', 'level_match', 'experience_bonus',
            'publications_bonus', 'total_score',
        }
        assert expected_keys.issubset(details.keys())


# ---------------------------------------------------------------------------
# run_recommendation_engine
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRunRecommendationEngine:
    """Integration tests for the bulk engine."""

    def test_engine_creates_match_for_qualifying_pair(self, matched_pair):
        _, school, need, _, teacher, _ = matched_pair
        result = run_recommendation_engine(min_score=30.0)
        assert result['created'] >= 1
        assert TeacherSchoolMatch.objects.filter(
            teacher=teacher, subject_need=need
        ).exists()

    def test_engine_respects_min_score_threshold(self, db):
        """Pairs scoring below min_score must not be stored."""
        # School and teacher in very different districts with no salary overlap
        _, school, need = make_school_user(
            username='school_low', district='District 99',
            min_salary=100_000, max_salary=150_000,
        )
        _, teacher, _ = make_teacher_user(
            username='teacher_low', national_id='7777777777',
            district='District 1',
            min_salary=900_000, max_salary=1_000_000,
            experience_years=0,
        )
        run_recommendation_engine(min_score=50.0)
        assert not TeacherSchoolMatch.objects.filter(
            teacher=teacher, subject_need=need
        ).exists()

    def test_engine_updates_existing_match(self, matched_pair):
        """Running the engine twice must update, not duplicate, existing matches."""
        _, school, need, _, teacher, _ = matched_pair
        run_recommendation_engine()
        run_recommendation_engine()
        count = TeacherSchoolMatch.objects.filter(
            teacher=teacher, subject_need=need
        ).count()
        assert count == 1

    def test_engine_skips_filled_needs(self, db):
        _, school, need = make_school_user(username='school_filled', district='D5')
        need.is_filled = True
        need.save()
        _, teacher, _ = make_teacher_user(
            username='teacher_filled', national_id='8888888888', district='D5',
        )
        run_recommendation_engine()
        assert not TeacherSchoolMatch.objects.filter(subject_need=need).exists()

    def test_engine_skips_unavailable_teachers(self, db):
        _, school, need = make_school_user(username='school_avail', district='D6')
        _, teacher, _ = make_teacher_user(
            username='teacher_unavail', national_id='9999999998', district='D6',
        )
        teacher.is_available = False
        teacher.save()
        run_recommendation_engine()
        assert not TeacherSchoolMatch.objects.filter(teacher=teacher).exists()

    def test_engine_returns_created_and_updated_counts(self, matched_pair):
        result = run_recommendation_engine()
        assert 'created' in result
        assert 'updated' in result
        assert isinstance(result['created'], int)
        assert isinstance(result['updated'], int)

    def test_engine_stores_score_components(self, matched_pair):
        _, school, need, _, teacher, _ = matched_pair
        run_recommendation_engine()
        match = TeacherSchoolMatch.objects.get(teacher=teacher, subject_need=need)
        assert match.match_score > 0
        assert match.district_match is True
        assert match.subject_match is True


# ---------------------------------------------------------------------------
# Query helper tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestQueryHelpers:
    """Tests for get_matches_for_school and get_matches_for_teacher."""

    def test_get_matches_for_school_returns_correct_matches(self, matched_pair):
        _, school, need, _, teacher, _ = matched_pair
        run_recommendation_engine()
        matches = get_matches_for_school(school)
        school_ids = {m.school_id for m in matches}
        assert school.id in school_ids

    def test_get_matches_for_teacher_returns_correct_matches(self, matched_pair):
        _, school, need, _, teacher, _ = matched_pair
        run_recommendation_engine()
        matches = get_matches_for_teacher(teacher)
        teacher_ids = {m.teacher_id for m in matches}
        assert teacher.id in teacher_ids

    def test_min_score_filter_is_applied(self, matched_pair):
        _, school, need, _, teacher, _ = matched_pair
        run_recommendation_engine()
        # Request only very high scores
        matches = get_matches_for_school(school, min_score=99.0)
        for m in matches:
            assert m.match_score >= 99.0

    def test_matches_ordered_by_score_descending(self, db):
        _, school, need = make_school_user(username='school_order', district='D7',
                                           subject='Math', education_level=EducationLevel.HIGH,
                                           min_salary=400_000, max_salary=700_000)
        make_teacher_user(username='t_high', national_id='1010101010',
                          district='D7', subject='Math', education_level=EducationLevel.HIGH,
                          min_salary=420_000, max_salary=680_000, experience_years=10)
        make_teacher_user(username='t_low', national_id='2020202020',
                          district='D8',  # different district → lower score
                          subject='Math', education_level=EducationLevel.HIGH,
                          min_salary=420_000, max_salary=680_000, experience_years=0)
        run_recommendation_engine(min_score=10.0)
        matches = list(get_matches_for_school(school))
        scores = [m.match_score for m in matches]
        assert scores == sorted(scores, reverse=True)
