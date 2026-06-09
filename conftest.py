"""
Root pytest configuration.

Provides shared fixtures used across all test modules:
  - db_setup     : alias for pytest-django's db fixture
  - school_user  : an authenticated school User + School + SubjectNeed
  - teacher_user : an authenticated teacher User + Teacher + TeachingSubject
  - api_client   : a DRF APIClient helper
  - school_client / teacher_client : pre-authenticated API clients
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from schools.models import School, SubjectNeed, SchoolType, EducationLevel
from teachers.models import Teacher, TeachingSubject


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def make_school_user(
    username: str = 'school_test',
    password: str = 'testpass123',
    district: str = 'District 5',
    name: str = 'Test School',
    school_type: str = SchoolType.BOYS,
    education_level: str = EducationLevel.HIGH,
    min_salary: int = 500_000,
    max_salary: int = 800_000,
    subject: str = 'Physics',
):
    """Create a User + School + SubjectNeed and return (user, school, need)."""
    user = User.objects.create_user(username=username, password=password)
    school = School.objects.create(
        user=user,
        name=name,
        school_type=school_type,
        education_level=education_level,
        phone='02111111111',
        district=district,
        address='123 Test Street',
    )
    need = SubjectNeed.objects.create(
        school=school,
        subject_name=subject,
        education_level=education_level,
        min_salary_per_hour=min_salary,
        max_salary_per_hour=max_salary,
    )
    return user, school, need


def make_teacher_user(
    username: str = 'teacher_test',
    password: str = 'testpass123',
    district: str = 'District 5',
    first_name: str = 'Ali',
    last_name: str = 'Mohammadi',
    national_id: str = '1234567890',
    education_level: str = EducationLevel.HIGH,
    min_salary: int = 480_000,
    max_salary: int = 820_000,
    experience_years: int = 5,
    subject: str = 'Physics',
):
    """Create a User + Teacher + TeachingSubject and return (user, teacher, subject_obj)."""
    user = User.objects.create_user(username=username, password=password)
    teacher = Teacher.objects.create(
        user=user,
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
        phone='09121234567',
        education_level=education_level,
        district=district,
        experience_years=experience_years,
        min_salary_per_hour=min_salary,
        max_salary_per_hour=max_salary,
    )
    subj = TeachingSubject.objects.create(
        teacher=teacher,
        subject_name=subject,
        education_level=education_level,
        years_of_experience=experience_years,
    )
    return user, teacher, subj


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """Return a bare (unauthenticated) APIClient."""
    return APIClient()


@pytest.fixture
def school_data(db):
    """Create and return (user, school, subject_need) for a school."""
    return make_school_user()


@pytest.fixture
def teacher_data(db):
    """Create and return (user, teacher, teaching_subject) for a teacher."""
    return make_teacher_user()


@pytest.fixture
def school_client(db, school_data):
    """Return an APIClient authenticated as the test school."""
    user, school, need = school_data
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.fixture
def teacher_client(db, teacher_data):
    """Return an APIClient authenticated as the test teacher."""
    user, teacher, subj = teacher_data
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.fixture
def matched_pair(db):
    """
    Create a school + teacher pair that should score 100 % against each other,
    and return (school_user, school, need, teacher_user, teacher, subj).
    """
    s_user, school, need = make_school_user(
        username='school_match',
        district='District 3',
        subject='Chemistry',
        education_level=EducationLevel.HIGH,
        min_salary=400_000,
        max_salary=700_000,
    )
    t_user, teacher, subj = make_teacher_user(
        username='teacher_match',
        national_id='9876543210',
        district='District 3',
        subject='Chemistry',
        education_level=EducationLevel.HIGH,
        min_salary=420_000,
        max_salary=680_000,
        experience_years=10,
    )
    return s_user, school, need, t_user, teacher, subj
