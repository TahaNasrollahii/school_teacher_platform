"""
Model-level unit tests.

Covers __str__, properties, Meta settings, and field constraints.
"""

import pytest
from django.db import IntegrityError

from schools.models import School, SubjectNeed, SchoolType, EducationLevel
from teachers.models import Teacher, TeachingSubject
from recommender.models import TeacherSchoolMatch, MatchStatus
from conftest import make_school_user, make_teacher_user


@pytest.mark.django_db
class TestSchoolModel:

    def test_str_contains_name_and_district(self, school_data):
        _, school, _ = school_data
        assert school.name in str(school)
        assert school.district in str(school)

    def test_default_is_not_verified(self, school_data):
        _, school, _ = school_data
        assert not school.is_verified

    def test_education_level_choices_valid(self):
        valid = {c[0] for c in EducationLevel.choices}
        assert 'primary' in valid
        assert 'middle' in valid
        assert 'high' in valid

    def test_school_type_choices_valid(self):
        valid = {c[0] for c in SchoolType.choices}
        assert 'girls' in valid
        assert 'boys' in valid
        assert 'mixed' in valid


@pytest.mark.django_db
class TestSubjectNeedModel:

    def test_str_contains_school_and_subject(self, school_data):
        _, school, need = school_data
        s = str(need)
        assert school.name in s
        assert need.subject_name in s

    def test_default_is_not_filled(self, school_data):
        _, _, need = school_data
        assert not need.is_filled

    def test_related_name_from_school(self, school_data):
        _, school, need = school_data
        assert need in school.subject_needs.all()


@pytest.mark.django_db
class TestTeacherModel:

    def test_full_name_property(self, teacher_data):
        _, teacher, _ = teacher_data
        assert teacher.full_name == f'{teacher.first_name} {teacher.last_name}'

    def test_str_contains_name_and_district(self, teacher_data):
        _, teacher, _ = teacher_data
        s = str(teacher)
        assert teacher.first_name in s
        assert teacher.district in s

    def test_default_is_available(self, teacher_data):
        _, teacher, _ = teacher_data
        assert teacher.is_available

    def test_national_id_uniqueness_enforced(self, db, teacher_data):
        _, teacher, _ = teacher_data
        from django.contrib.auth.models import User
        user2 = User.objects.create_user(username='dup_nat_id', password='pass')
        with pytest.raises(IntegrityError):
            Teacher.objects.create(
                user=user2,
                first_name='Dup',
                last_name='Test',
                national_id=teacher.national_id,  # duplicate
                phone='09000000000',
                education_level=EducationLevel.HIGH,
                district='D1',
                min_salary_per_hour=100_000,
                max_salary_per_hour=200_000,
            )


@pytest.mark.django_db
class TestTeachingSubjectModel:

    def test_str_contains_teacher_and_subject(self, teacher_data):
        _, teacher, subj = teacher_data
        s = str(subj)
        assert teacher.first_name in s
        assert subj.subject_name in s

    def test_unique_together_prevents_duplicate(self, db, teacher_data):
        _, teacher, subj = teacher_data
        with pytest.raises(IntegrityError):
            TeachingSubject.objects.create(
                teacher=teacher,
                subject_name=subj.subject_name,       # duplicate
                education_level=subj.education_level,  # duplicate
                years_of_experience=1,
            )

    def test_related_name_from_teacher(self, teacher_data):
        _, teacher, subj = teacher_data
        assert subj in teacher.subjects.all()


@pytest.mark.django_db
class TestTeacherSchoolMatchModel:

    def test_str_format(self, matched_pair):
        from recommender.engine import run_recommendation_engine
        _, school, need, _, teacher, _ = matched_pair
        run_recommendation_engine()
        match = TeacherSchoolMatch.objects.get(teacher=teacher, subject_need=need)
        s = str(match)
        assert teacher.first_name in s
        assert school.name in s
        assert '%' in s

    def test_default_status_is_pending(self, matched_pair):
        from recommender.engine import run_recommendation_engine
        _, school, need, _, teacher, _ = matched_pair
        run_recommendation_engine()
        match = TeacherSchoolMatch.objects.get(teacher=teacher, subject_need=need)
        assert match.status == MatchStatus.PENDING

    def test_unique_together_teacher_subject_need(self, matched_pair):
        from recommender.engine import run_recommendation_engine
        _, school, need, _, teacher, _ = matched_pair
        run_recommendation_engine()
        with pytest.raises(IntegrityError):
            TeacherSchoolMatch.objects.create(
                teacher=teacher,
                school=school,
                subject_need=need,
                match_score=50.0,
            )

    def test_ordering_by_score_descending(self, db):
        """Default queryset must be ordered highest score first."""
        _, school, need = make_school_user(username='school_ord', district='D8',
                                           subject='Math', education_level=EducationLevel.HIGH,
                                           min_salary=400_000, max_salary=700_000)
        _, t1, _ = make_teacher_user(username='t1_ord', national_id='1111000011',
                                     district='D8', subject='Math',
                                     education_level=EducationLevel.HIGH,
                                     min_salary=420_000, max_salary=680_000, experience_years=10)
        _, t2, _ = make_teacher_user(username='t2_ord', national_id='2222000022',
                                     district='D9',   # different district → lower score
                                     subject='Math', education_level=EducationLevel.HIGH,
                                     min_salary=420_000, max_salary=680_000, experience_years=0)
        from recommender.engine import run_recommendation_engine
        run_recommendation_engine(min_score=10.0)
        matches = list(TeacherSchoolMatch.objects.filter(school=school))
        scores = [m.match_score for m in matches]
        assert scores == sorted(scores, reverse=True)
