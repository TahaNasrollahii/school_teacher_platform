"""
Tests for the teachers app.

Covers:
  - Teacher registration (success + validation failures)
  - Teacher login (success, wrong password, school-account rejection)
  - Profile read / update
  - TeachingSubject CRUD
  - Public teacher list filtering
"""

import pytest
from django.contrib.auth.models import User

from schools.models import EducationLevel
from teachers.models import Teacher, TeachingSubject
from conftest import make_teacher_user, make_school_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTER_URL = '/api/teachers/register/'
LOGIN_URL = '/api/teachers/login/'
PROFILE_URL = '/api/teachers/profile/'
SUBJECTS_URL = '/api/teachers/subjects/'
LIST_URL = '/api/teachers/list/'

VALID_PAYLOAD = {
    'username': 'new_teacher',
    'password': 'securepass99',
    'first_name': 'Sara',
    'last_name': 'Mousavi',
    'national_id': '3344556677',
    'phone': '09126666666',
    'education_level': EducationLevel.HIGH,
    'district': 'District 3',
    'experience_years': 7,
    'min_salary_per_hour': 500_000,
    'max_salary_per_hour': 900_000,
    'subjects': [
        {
            'subject_name': 'Physics',
            'education_level': EducationLevel.HIGH,
            'years_of_experience': 7,
        }
    ],
}


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTeacherRegistration:
    """Tests for POST /api/teachers/register/."""

    def test_successful_registration_returns_201(self, api_client):
        response = api_client.post(REGISTER_URL, VALID_PAYLOAD, format='json')
        assert response.status_code == 201
        assert 'token' in response.data
        assert 'teacher_id' in response.data

    def test_registration_creates_user_teacher_and_subjects(self, api_client):
        api_client.post(REGISTER_URL, VALID_PAYLOAD, format='json')
        assert User.objects.filter(username='new_teacher').exists()
        teacher = Teacher.objects.get(national_id='3344556677')
        assert teacher.subjects.count() == 1

    def test_duplicate_username_returns_400(self, api_client, teacher_data):
        user, _, _ = teacher_data
        payload = {**VALID_PAYLOAD, 'username': user.username}
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_duplicate_national_id_returns_400(self, api_client, teacher_data):
        _, teacher, _ = teacher_data
        payload = {
            **VALID_PAYLOAD,
            'username': 'another_teacher',
            'national_id': teacher.national_id,
        }
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_non_digit_national_id_returns_400(self, api_client):
        payload = {**VALID_PAYLOAD, 'username': 'alpha_id', 'national_id': 'ABCDEFGHIJ'}
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_national_id_too_short_returns_400(self, api_client):
        payload = {**VALID_PAYLOAD, 'username': 'short_id', 'national_id': '12345'}
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_invalid_salary_range_returns_400(self, api_client):
        payload = {
            **VALID_PAYLOAD,
            'username': 'bad_salary',
            'national_id': '0011223344',
            'min_salary_per_hour': 900_000,
            'max_salary_per_hour': 400_000,
        }
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_empty_subjects_returns_400(self, api_client):
        payload = {**VALID_PAYLOAD, 'username': 'no_subj', 'national_id': '5566778899', 'subjects': []}
        response = api_client.post(REGISTER_URL, payload, format='json')
        assert response.status_code == 400

    def test_full_name_in_response(self, api_client):
        response = api_client.post(REGISTER_URL, VALID_PAYLOAD, format='json')
        assert response.data.get('full_name') == 'Sara Mousavi'

    def test_multiple_subjects_stored(self, api_client):
        payload = {
            **VALID_PAYLOAD,
            'username': 'multi_subj',
            'national_id': '1122334455',
            'subjects': [
                {'subject_name': 'Physics', 'education_level': EducationLevel.HIGH, 'years_of_experience': 5},
                {'subject_name': 'Math', 'education_level': EducationLevel.HIGH, 'years_of_experience': 3},
            ],
        }
        api_client.post(REGISTER_URL, payload, format='json')
        teacher = Teacher.objects.get(national_id='1122334455')
        assert teacher.subjects.count() == 2


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTeacherLogin:
    """Tests for POST /api/teachers/login/."""

    def test_valid_credentials_return_token(self, api_client, teacher_data):
        user, teacher, _ = teacher_data
        response = api_client.post(
            LOGIN_URL,
            {'username': user.username, 'password': 'testpass123'},
            format='json',
        )
        assert response.status_code == 200
        assert 'token' in response.data
        assert response.data['full_name'] == teacher.full_name

    def test_wrong_password_returns_401(self, api_client, teacher_data):
        user, _, _ = teacher_data
        response = api_client.post(
            LOGIN_URL,
            {'username': user.username, 'password': 'bad_password'},
            format='json',
        )
        assert response.status_code == 401

    def test_school_account_rejected_by_teacher_login(self, api_client, db):
        """Teacher login endpoint must reject school credentials."""
        make_school_user(username='school_for_teacher_test')
        response = api_client.post(
            LOGIN_URL,
            {'username': 'school_for_teacher_test', 'password': 'testpass123'},
            format='json',
        )
        assert response.status_code == 401

    def test_nonexistent_user_returns_401(self, api_client, db):
        response = api_client.post(
            LOGIN_URL,
            {'username': 'ghost', 'password': 'whatever'},
            format='json',
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Profile tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTeacherProfile:
    """Tests for GET/PUT /api/teachers/profile/."""

    def test_authenticated_teacher_can_read_profile(self, teacher_client, teacher_data):
        _, teacher, _ = teacher_data
        response = teacher_client.get(PROFILE_URL)
        assert response.status_code == 200
        assert response.data['full_name'] == teacher.full_name

    def test_unauthenticated_request_returns_401(self, api_client):
        response = api_client.get(PROFILE_URL)
        assert response.status_code == 401

    def test_teacher_can_update_district(self, teacher_client):
        response = teacher_client.patch(
            PROFILE_URL,
            {'district': 'District 12'},
            format='json',
        )
        assert response.status_code == 200
        assert response.data['district'] == 'District 12'

    def test_profile_contains_subjects(self, teacher_client):
        response = teacher_client.get(PROFILE_URL)
        assert len(response.data['subjects']) == 1

    def test_full_name_property_in_response(self, teacher_client, teacher_data):
        _, teacher, _ = teacher_data
        response = teacher_client.get(PROFILE_URL)
        assert response.data['full_name'] == f'{teacher.first_name} {teacher.last_name}'


# ---------------------------------------------------------------------------
# TeachingSubject CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTeachingSubjectCRUD:
    """Tests for /api/teachers/subjects/ endpoints."""

    def test_list_subjects(self, teacher_client):
        response = teacher_client.get(SUBJECTS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_add_new_subject(self, teacher_client):
        payload = {
            'subject_name': 'Chemistry',
            'education_level': EducationLevel.HIGH,
            'years_of_experience': 2,
        }
        response = teacher_client.post(SUBJECTS_URL, payload, format='json')
        assert response.status_code == 201
        assert response.data['subject_name'] == 'Chemistry'

    def test_delete_subject(self, teacher_client, teacher_data):
        _, _, subj = teacher_data
        url = f'{SUBJECTS_URL}{subj.pk}/'
        response = teacher_client.delete(url)
        assert response.status_code == 204
        assert not TeachingSubject.objects.filter(pk=subj.pk).exists()

    def test_update_subject_experience(self, teacher_client, teacher_data):
        _, _, subj = teacher_data
        url = f'{SUBJECTS_URL}{subj.pk}/'
        response = teacher_client.patch(url, {'years_of_experience': 10}, format='json')
        assert response.status_code == 200
        subj.refresh_from_db()
        assert subj.years_of_experience == 10

    def test_cannot_access_another_teachers_subject(self, db, teacher_client):
        _, other_teacher, other_subj = make_teacher_user(
            username='other_teacher', national_id='9999999999'
        )
        url = f'{SUBJECTS_URL}{other_subj.pk}/'
        response = teacher_client.get(url)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Teacher list / filter tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTeacherListFilter:
    """Tests for GET /api/teachers/list/."""

    def test_list_returns_available_teachers(self, teacher_client, teacher_data):
        response = teacher_client.get(LIST_URL)
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_unavailable_teacher_excluded(self, teacher_client, teacher_data, db):
        _, teacher, _ = teacher_data
        teacher.is_available = False
        teacher.save()
        response = teacher_client.get(LIST_URL)
        ids = [t['id'] for t in response.data['results']]
        assert teacher.id not in ids

    def test_filter_by_district(self, teacher_client, db):
        make_teacher_user(username='teacher_d11', national_id='1231231230',
                          district='District 11')
        response = teacher_client.get(LIST_URL, {'district': 'District 11'})
        assert response.status_code == 200
        for item in response.data['results']:
            assert 'District 11' in item['district']

    def test_filter_by_subject(self, teacher_client, teacher_data):
        response = teacher_client.get(LIST_URL, {'subject': 'Physics'})
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_filter_by_nonexistent_subject_returns_empty(self, teacher_client, teacher_data):
        response = teacher_client.get(LIST_URL, {'subject': 'Underwater Basket Weaving'})
        assert response.data['count'] == 0

    def test_unauthenticated_list_returns_401(self, api_client):
        response = api_client.get(LIST_URL)
        assert response.status_code == 401
