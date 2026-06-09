"""
Tests for the schools app.

Covers:
  - School registration (success + validation failures)
  - School login (success, wrong password, teacher-account rejection)
  - Profile read / update
  - SubjectNeed CRUD
  - Public school list filtering
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from schools.models import School, SubjectNeed, SchoolType, EducationLevel
from conftest import make_school_user, make_teacher_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTER_URL = '/api/schools/register/'
LOGIN_URL = '/api/schools/login/'
PROFILE_URL = '/api/schools/profile/'
NEEDS_URL = '/api/schools/subject-needs/'
LIST_URL = '/api/schools/list/'

VALID_PAYLOAD = {
    'username': 'school_new',
    'password': 'securepass99',
    'name': 'New Test School',
    'school_type': SchoolType.GIRLS,
    'education_level': EducationLevel.HIGH,
    'phone': '02100000001',
    'district': 'District 7',
    'address': '10 Main St',
    'subject_needs': [
        {
            'subject_name': 'Math',
            'education_level': EducationLevel.HIGH,
            'min_salary_per_hour': 400_000,
            'max_salary_per_hour': 700_000,
        }
    ],
}


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSchoolRegistration:
    """Tests for POST /api/schools/register/."""

    def test_successful_registration_returns_201(self, api_client):
        response = api_client.post(REGISTER_URL, VALID_PAYLOAD, format='json')
        assert response.status_code == 201
        assert 'token' in response.data
        assert 'school_id' in response.data

    def test_registration_creates_user_school_and_needs(self, api_client):
        api_client.post(REGISTER_URL, VALID_PAYLOAD, format='json')
        assert User.objects.filter(username='school_new').exists()
        school = School.objects.get(name='New Test School')
        assert school.subject_needs.count() == 1

    def test_duplicate_username_returns_400(self, api_client, school_data):
        """Second registration with the same username must be rejected."""
        _, school, _ = school_data
        payload = {**VALID_PAYLOAD, 'username': school.user.username}
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_missing_subject_needs_returns_400(self, api_client):
        payload = {**VALID_PAYLOAD, 'username': 'another_school', 'subject_needs': []}
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_invalid_salary_range_returns_400(self, api_client):
        """min > max must be rejected."""
        payload = {
            **VALID_PAYLOAD,
            'username': 'salary_test',
            'subject_needs': [
                {
                    'subject_name': 'Biology',
                    'education_level': EducationLevel.HIGH,
                    'min_salary_per_hour': 900_000,   # higher than max
                    'max_salary_per_hour': 500_000,
                }
            ],
        }
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_short_password_returns_400(self, api_client):
        payload = {**VALID_PAYLOAD, 'username': 'short_pw', 'password': '123'}
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_response_contains_school_name(self, api_client):
        response = api_client.post(REGISTER_URL, VALID_PAYLOAD, format='json')
        assert response.data.get('school_name') == 'New Test School'

    def test_multiple_subject_needs_are_stored(self, api_client):
        payload = {
            **VALID_PAYLOAD,
            'username': 'multi_need_school',
            'subject_needs': [
                {'subject_name': 'Math', 'education_level': EducationLevel.HIGH,
                 'min_salary_per_hour': 400_000, 'max_salary_per_hour': 700_000},
                {'subject_name': 'Physics', 'education_level': EducationLevel.HIGH,
                 'min_salary_per_hour': 450_000, 'max_salary_per_hour': 750_000},
            ],
        }
        api_client.post(REGISTER_URL, payload, format='json')
        school = School.objects.get(name='New Test School')
        assert school.subject_needs.count() == 2


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSchoolLogin:
    """Tests for POST /api/schools/login/."""

    def test_valid_credentials_return_token(self, api_client, school_data):
        user, school, _ = school_data
        response = api_client.post(
            LOGIN_URL,
            {'username': user.username, 'password': 'testpass123'},
            format='json',
        )
        assert response.status_code == 200
        assert 'token' in response.data
        assert response.data['school_name'] == school.name

    def test_wrong_password_returns_401(self, api_client, school_data):
        user, _, _ = school_data
        response = api_client.post(
            LOGIN_URL,
            {'username': user.username, 'password': 'wrongpassword'},
            format='json',
        )
        assert response.status_code == 401

    def test_teacher_account_rejected(self, api_client, db):
        """School login endpoint must reject teacher credentials."""
        t_user, _, _ = make_teacher_user(username='teacher_login_test',
                                         national_id='1111111111')
        response = api_client.post(
            LOGIN_URL,
            {'username': 'teacher_login_test', 'password': 'testpass123'},
            format='json',
        )
        assert response.status_code == 401

    def test_nonexistent_user_returns_401(self, api_client, db):
        response = api_client.post(
            LOGIN_URL,
            {'username': 'nobody', 'password': 'whatever'},
            format='json',
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Profile tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSchoolProfile:
    """Tests for GET/PUT /api/schools/profile/."""

    def test_authenticated_user_can_read_profile(self, school_client, school_data):
        _, school, _ = school_data
        response = school_client.get(PROFILE_URL)
        assert response.status_code == 200
        assert response.data['name'] == school.name

    def test_unauthenticated_request_returns_401(self, api_client):
        response = api_client.get(PROFILE_URL)
        assert response.status_code == 401

    def test_school_can_update_phone(self, school_client, school_data):
        response = school_client.patch(
            PROFILE_URL,
            {'phone': '09000000001'},
            format='json',
        )
        assert response.status_code == 200
        assert response.data['phone'] == '09000000001'

    def test_profile_includes_subject_needs(self, school_client, school_data):
        _, school, _ = school_data
        response = school_client.get(PROFILE_URL)
        assert len(response.data['subject_needs']) == 1


# ---------------------------------------------------------------------------
# SubjectNeed CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSubjectNeedCRUD:
    """Tests for /api/schools/subject-needs/ endpoints."""

    def test_list_needs_for_authenticated_school(self, school_client, school_data):
        response = school_client.get(NEEDS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_create_new_subject_need(self, school_client):
        payload = {
            'subject_name': 'Chemistry',
            'education_level': EducationLevel.HIGH,
            'min_salary_per_hour': 300_000,
            'max_salary_per_hour': 600_000,
        }
        response = school_client.post(NEEDS_URL, payload, format='json')
        assert response.status_code == 201
        assert response.data['subject_name'] == 'Chemistry'

    def test_delete_subject_need(self, school_client, school_data):
        _, _, need = school_data
        url = f'{NEEDS_URL}{need.pk}/'
        response = school_client.delete(url)
        assert response.status_code == 204
        assert not SubjectNeed.objects.filter(pk=need.pk).exists()

    def test_update_subject_need_salary(self, school_client, school_data):
        _, _, need = school_data
        url = f'{NEEDS_URL}{need.pk}/'
        response = school_client.patch(
            url,
            {'min_salary_per_hour': 350_000, 'max_salary_per_hour': 650_000},
            format='json',
        )
        assert response.status_code == 200
        need.refresh_from_db()
        assert need.min_salary_per_hour == 350_000

    def test_cannot_access_another_schools_need(self, db, school_client):
        """A school must not be able to modify another school's subject need."""
        _, other_school, other_need = make_school_user(
            username='other_school', district='District 2'
        )
        url = f'{NEEDS_URL}{other_need.pk}/'
        response = school_client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# School list / filter tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSchoolListFilter:
    """Tests for GET /api/schools/list/."""

    def test_list_returns_all_schools(self, school_client, school_data):
        response = school_client.get(LIST_URL)
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_filter_by_district(self, school_client, school_data, db):
        # Create a second school in a different district
        make_school_user(username='school_d9', district='District 9')
        response = school_client.get(LIST_URL, {'district': 'District 9'})
        assert response.status_code == 200
        for item in response.data['results']:
            assert 'District 9' in item['district']

    def test_filter_by_level(self, school_client, school_data):
        response = school_client.get(LIST_URL, {'level': EducationLevel.HIGH})
        assert response.status_code == 200
        for item in response.data['results']:
            assert item['education_level'] == EducationLevel.HIGH

    def test_unauthenticated_list_returns_401(self, api_client):
        response = api_client.get(LIST_URL)
        assert response.status_code == 401
