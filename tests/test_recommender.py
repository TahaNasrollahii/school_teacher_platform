"""
Tests for the recommender API views.

Covers:
  - GET school-matches / teacher-matches (auth, auto-run, filtering)
  - PATCH school-match/status and teacher-match/status (workflow transitions)
  - POST refresh endpoint
  - GET stats endpoint
  - POST admin run endpoint
"""

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from recommender.engine import run_recommendation_engine
from recommender.models import TeacherSchoolMatch, MatchStatus
from conftest import make_school_user, make_teacher_user


SCHOOL_MATCHES_URL = '/api/recommend/school-matches/'
TEACHER_MATCHES_URL = '/api/recommend/teacher-matches/'
REFRESH_URL = '/api/recommend/refresh/'
STATS_URL = '/api/recommend/stats/'
ADMIN_RUN_URL = '/api/recommend/run/'


def make_authenticated_client(user) -> APIClient:
    """Return an APIClient pre-authenticated for *user*."""
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


# ---------------------------------------------------------------------------
# School matches endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSchoolMatchesView:

    def test_returns_matches_for_school(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        client = make_authenticated_client(s_user)
        response = client.get(SCHOOL_MATCHES_URL)
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(SCHOOL_MATCHES_URL)
        assert response.status_code == 401

    def test_auto_runs_engine_on_first_access(self, matched_pair):
        """
        If no matches exist yet, the view should trigger the engine
        automatically so the user always gets results.
        """
        s_user, school, need, t_user, teacher, _ = matched_pair
        assert TeacherSchoolMatch.objects.filter(school=school).count() == 0
        client = make_authenticated_client(s_user)
        response = client.get(SCHOOL_MATCHES_URL)
        assert response.status_code == 200
        assert TeacherSchoolMatch.objects.filter(school=school).count() >= 1

    def test_filter_by_min_score(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        client = make_authenticated_client(s_user)
        response = client.get(SCHOOL_MATCHES_URL, {'min_score': 95})
        for item in response.data['results']:
            assert item['match_score'] >= 95

    def test_filter_by_subject_id(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        client = make_authenticated_client(s_user)
        response = client.get(SCHOOL_MATCHES_URL, {'subject_id': need.pk})
        for item in response.data['results']:
            assert item['subject_name'] == need.subject_name

    def test_response_contains_score_breakdown(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        client = make_authenticated_client(s_user)
        response = client.get(SCHOOL_MATCHES_URL)
        first = response.data['results'][0]
        assert 'match_score' in first
        assert 'district_match' in first
        assert 'subject_match' in first
        assert 'teacher_salary_range' in first
        assert 'school_salary_range' in first


# ---------------------------------------------------------------------------
# Teacher matches endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTeacherMatchesView:

    def test_returns_matches_for_teacher(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        client = make_authenticated_client(t_user)
        response = client.get(TEACHER_MATCHES_URL)
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(TEACHER_MATCHES_URL)
        assert response.status_code == 401

    def test_auto_runs_engine_on_first_access(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        assert TeacherSchoolMatch.objects.filter(teacher=teacher).count() == 0
        client = make_authenticated_client(t_user)
        response = client.get(TEACHER_MATCHES_URL)
        assert response.status_code == 200
        assert TeacherSchoolMatch.objects.filter(teacher=teacher).count() >= 1

    def test_teacher_sees_only_own_matches(self, db, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        # Create a second teacher with different match
        _, other_school, other_need = make_school_user(
            username='other_school_rec', district='District Z',
            subject='Art', education_level='primary',
        )
        _, other_teacher, _ = make_teacher_user(
            username='other_teacher_rec', national_id='0000000001',
            district='District Z', subject='Art', education_level='primary',
        )
        run_recommendation_engine()
        client = make_authenticated_client(t_user)
        response = client.get(TEACHER_MATCHES_URL)
        teacher_names = {r['teacher_name'] for r in response.data['results']}
        assert all(name == teacher.full_name for name in teacher_names)


# ---------------------------------------------------------------------------
# Match status workflow
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMatchStatusWorkflow:

    def _get_match(self, matched_pair):
        _, school, need, _, teacher, _ = matched_pair
        run_recommendation_engine()
        return TeacherSchoolMatch.objects.get(teacher=teacher, subject_need=need)

    def test_school_can_express_interest(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        match = self._get_match(matched_pair)
        client = make_authenticated_client(s_user)
        url = f'/api/recommend/school-match/{match.pk}/status/'
        response = client.patch(url, {'status': MatchStatus.SCHOOL_INTERESTED}, format='json')
        assert response.status_code == 200
        match.refresh_from_db()
        assert match.status == MatchStatus.SCHOOL_INTERESTED

    def test_teacher_can_express_interest(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        match = self._get_match(matched_pair)
        client = make_authenticated_client(t_user)
        url = f'/api/recommend/teacher-match/{match.pk}/status/'
        response = client.patch(url, {'status': MatchStatus.TEACHER_INTERESTED}, format='json')
        assert response.status_code == 200
        match.refresh_from_db()
        assert match.status == MatchStatus.TEACHER_INTERESTED

    def test_mutual_interest_advances_to_mutual(self, matched_pair):
        """When both sides express interest, status must become MUTUAL."""
        s_user, school, need, t_user, teacher, _ = matched_pair
        match = self._get_match(matched_pair)

        # School expresses interest first
        s_client = make_authenticated_client(s_user)
        s_client.patch(
            f'/api/recommend/school-match/{match.pk}/status/',
            {'status': MatchStatus.SCHOOL_INTERESTED}, format='json',
        )

        # Teacher expresses interest → should become mutual
        t_client = make_authenticated_client(t_user)
        response = t_client.patch(
            f'/api/recommend/teacher-match/{match.pk}/status/',
            {'status': MatchStatus.TEACHER_INTERESTED}, format='json',
        )
        assert response.status_code == 200
        match.refresh_from_db()
        assert match.status == MatchStatus.MUTUAL

    def test_reverse_mutual_also_works(self, matched_pair):
        """Teacher expresses interest first, school confirms → MUTUAL."""
        s_user, school, need, t_user, teacher, _ = matched_pair
        match = self._get_match(matched_pair)

        t_client = make_authenticated_client(t_user)
        t_client.patch(
            f'/api/recommend/teacher-match/{match.pk}/status/',
            {'status': MatchStatus.TEACHER_INTERESTED}, format='json',
        )

        s_client = make_authenticated_client(s_user)
        response = s_client.patch(
            f'/api/recommend/school-match/{match.pk}/status/',
            {'status': MatchStatus.SCHOOL_INTERESTED}, format='json',
        )
        assert response.status_code == 200
        match.refresh_from_db()
        assert match.status == MatchStatus.MUTUAL

    def test_school_can_reject_match(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        match = self._get_match(matched_pair)
        s_client = make_authenticated_client(s_user)
        url = f'/api/recommend/school-match/{match.pk}/status/'
        response = s_client.patch(url, {'status': MatchStatus.REJECTED}, format='json')
        assert response.status_code == 200
        match.refresh_from_db()
        assert match.status == MatchStatus.REJECTED

    def test_school_note_is_saved(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        match = self._get_match(matched_pair)
        s_client = make_authenticated_client(s_user)
        url = f'/api/recommend/school-match/{match.pk}/status/'
        note_text = 'Please contact us by Friday.'
        s_client.patch(url, {'status': MatchStatus.SCHOOL_INTERESTED, 'note': note_text},
                       format='json')
        match.refresh_from_db()
        assert match.school_note == note_text

    def test_teacher_note_is_saved(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        match = self._get_match(matched_pair)
        t_client = make_authenticated_client(t_user)
        url = f'/api/recommend/teacher-match/{match.pk}/status/'
        note_text = 'I am available from September.'
        t_client.patch(url, {'status': MatchStatus.TEACHER_INTERESTED, 'note': note_text},
                       format='json')
        match.refresh_from_db()
        assert match.teacher_note == note_text

    def test_school_cannot_update_another_schools_match(self, db, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        match = TeacherSchoolMatch.objects.get(teacher=teacher, subject_need=need)

        # Create a second school and try to update the first school's match
        other_user, other_school, _ = make_school_user(
            username='intruder_school', district='District X',
        )
        intruder = make_authenticated_client(other_user)
        url = f'/api/recommend/school-match/{match.pk}/status/'
        response = intruder.patch(url, {'status': MatchStatus.REJECTED}, format='json')
        assert response.status_code == 404

    def test_invalid_status_value_returns_400(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        match = TeacherSchoolMatch.objects.get(teacher=teacher, subject_need=need)
        s_client = make_authenticated_client(s_user)
        url = f'/api/recommend/school-match/{match.pk}/status/'
        response = s_client.patch(url, {'status': 'not_a_real_status'}, format='json')
        assert response.status_code == 400

    def test_nonexistent_match_returns_404(self, matched_pair):
        s_user, _, _, _, _, _ = matched_pair
        s_client = make_authenticated_client(s_user)
        response = s_client.patch(
            '/api/recommend/school-match/99999/status/',
            {'status': MatchStatus.SCHOOL_INTERESTED}, format='json',
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Refresh endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRefreshView:

    def test_authenticated_user_can_refresh(self, school_client):
        response = school_client.post(REFRESH_URL, format='json')
        assert response.status_code == 200
        assert 'matches_created' in response.data

    def test_unauthenticated_refresh_returns_401(self, api_client):
        response = api_client.post(REFRESH_URL)
        assert response.status_code == 401

    def test_refresh_with_custom_min_score(self, school_client, matched_pair):
        response = school_client.post(REFRESH_URL, {'min_score': 50}, format='json')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Stats endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMatchStatsView:

    def test_school_stats_contain_expected_fields(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        s_client = make_authenticated_client(s_user)
        response = s_client.get(STATS_URL)
        assert response.status_code == 200
        assert response.data['role'] == 'school'
        for key in ('total_matches', 'mutual_matches', 'avg_score', 'top_match_score'):
            assert key in response.data

    def test_teacher_stats_contain_expected_fields(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        t_client = make_authenticated_client(t_user)
        response = t_client.get(STATS_URL)
        assert response.status_code == 200
        assert response.data['role'] == 'teacher'

    def test_stats_counts_mutual_matches(self, matched_pair):
        s_user, school, need, t_user, teacher, _ = matched_pair
        run_recommendation_engine()
        match = TeacherSchoolMatch.objects.get(teacher=teacher, subject_need=need)
        match.status = MatchStatus.MUTUAL
        match.save()

        s_client = make_authenticated_client(s_user)
        response = s_client.get(STATS_URL)
        assert response.data['mutual_matches'] == 1

    def test_unauthenticated_stats_returns_401(self, api_client):
        response = api_client.get(STATS_URL)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Admin run endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminRunView:

    def test_non_admin_returns_403(self, school_client):
        response = school_client.post(ADMIN_RUN_URL)
        assert response.status_code == 403

    def test_admin_can_trigger_engine(self, db):
        from django.contrib.auth.models import User
        admin = User.objects.create_superuser(
            username='test_admin', password='adminpass', email='a@a.com'
        )
        client = make_authenticated_client(admin)
        response = client.post(ADMIN_RUN_URL, {'min_score': 30}, format='json')
        assert response.status_code == 200
        assert 'matches_created' in response.data
