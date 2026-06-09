from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from .models import TeacherSchoolMatch, MatchStatus
from .serializers import MatchSerializer, MatchStatusUpdateSerializer
from .engine import run_recommendation_engine, get_matches_for_school, get_matches_for_teacher


class RunRecommendationView(APIView):
    """
    POST /api/recommend/run/

    Admin-only endpoint that triggers a full engine run across all
    available teachers and unfilled subject needs.

    Accepts optional ``min_score`` body parameter (default 30.0).
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        min_score = float(request.data.get('min_score', 30.0))
        result = run_recommendation_engine(min_score=min_score)
        return Response({
            'message': _('Recommendation engine ran successfully.'),
            'matches_created': result['created'],
            'matches_updated': result['updated'],
        })


class SchoolMatchesView(generics.ListAPIView):
    """
    GET /api/recommend/school-matches/

    Returns the ranked list of suggested teachers for the authenticated
    school.  Runs the engine automatically on first access if no matches
    exist yet.

    Query parameters:
      - min_score   (float, default 30)
      - subject_id  (int, filter by a specific SubjectNeed pk)
    """
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        school = self.request.user.school_profile
        min_score = float(self.request.query_params.get('min_score', 30.0))
        subject_id = self.request.query_params.get('subject_id')
        qs = get_matches_for_school(school, min_score)
        if subject_id:
            qs = qs.filter(subject_need_id=subject_id)
        return qs

    def list(self, request, *args, **kwargs):
        # Auto-run engine on first visit if no matches have been computed yet
        school = request.user.school_profile
        if not TeacherSchoolMatch.objects.filter(school=school).exists():
            run_recommendation_engine()
        return super().list(request, *args, **kwargs)


class TeacherMatchesView(generics.ListAPIView):
    """
    GET /api/recommend/teacher-matches/

    Returns the ranked list of suggested schools for the authenticated
    teacher.  Runs the engine automatically on first access if no matches
    exist yet.

    Query parameters:
      - min_score  (float, default 30)
    """
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        teacher = self.request.user.teacher_profile
        min_score = float(self.request.query_params.get('min_score', 30.0))
        return get_matches_for_teacher(teacher, min_score)

    def list(self, request, *args, **kwargs):
        # Auto-run engine on first visit
        teacher = request.user.teacher_profile
        if not TeacherSchoolMatch.objects.filter(teacher=teacher).exists():
            run_recommendation_engine()
        return super().list(request, *args, **kwargs)


class SchoolUpdateMatchStatusView(APIView):
    """
    PATCH /api/recommend/school-match/<match_id>/status/

    Allows the school to express interest or reject a suggested teacher.
    If the teacher has already expressed interest, the status advances
    automatically to MUTUAL.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, match_id):
        try:
            match = TeacherSchoolMatch.objects.get(
                id=match_id, school=request.user.school_profile
            )
        except TeacherSchoolMatch.DoesNotExist:
            return Response(
                {'error': _('Match not found.')},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MatchStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data['status']
        note = serializer.validated_data.get('note', '')

        # Advance to mutual if the teacher has already expressed interest
        if (new_status == MatchStatus.SCHOOL_INTERESTED
                and match.status == MatchStatus.TEACHER_INTERESTED):
            match.status = MatchStatus.MUTUAL
        elif new_status == MatchStatus.SCHOOL_INTERESTED:
            match.status = MatchStatus.SCHOOL_INTERESTED
        else:
            match.status = new_status

        if note:
            match.school_note = note
        match.save()
        return Response(MatchSerializer(match).data)


class TeacherUpdateMatchStatusView(APIView):
    """
    PATCH /api/recommend/teacher-match/<match_id>/status/

    Allows the teacher to express interest or reject a suggested school.
    If the school has already expressed interest, the status advances
    automatically to MUTUAL.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, match_id):
        try:
            match = TeacherSchoolMatch.objects.get(
                id=match_id, teacher=request.user.teacher_profile
            )
        except TeacherSchoolMatch.DoesNotExist:
            return Response(
                {'error': _('Match not found.')},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MatchStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data['status']
        note = serializer.validated_data.get('note', '')

        # Advance to mutual if the school has already expressed interest
        if (new_status == MatchStatus.TEACHER_INTERESTED
                and match.status == MatchStatus.SCHOOL_INTERESTED):
            match.status = MatchStatus.MUTUAL
        elif new_status == MatchStatus.TEACHER_INTERESTED:
            match.status = MatchStatus.TEACHER_INTERESTED
        else:
            match.status = new_status

        if note:
            match.teacher_note = note
        match.save()
        return Response(MatchSerializer(match).data)


class RefreshMatchesView(APIView):
    """
    POST /api/recommend/refresh/

    Re-runs the recommendation engine.  Available to any authenticated user.
    Accepts optional ``min_score`` body parameter.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        min_score = float(request.data.get('min_score', 30.0))
        result = run_recommendation_engine(min_score=min_score)
        return Response({
            'message': _('Matches refreshed successfully.'),
            'matches_created': result['created'],
            'matches_updated': result['updated'],
        })


class MatchStatsView(APIView):
    """
    GET /api/recommend/stats/

    Returns aggregate match statistics for the authenticated user.
    Distinguishes between school and teacher callers automatically.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if hasattr(user, 'school_profile'):
            school = user.school_profile
            matches = TeacherSchoolMatch.objects.filter(school=school)
            scores = list(matches.values_list('match_score', flat=True))
            return Response({
                'role': 'school',
                'total_matches': len(scores),
                'mutual_matches': matches.filter(status=MatchStatus.MUTUAL).count(),
                'school_interested': matches.filter(
                    status=MatchStatus.SCHOOL_INTERESTED).count(),
                'teacher_interested': matches.filter(
                    status=MatchStatus.TEACHER_INTERESTED).count(),
                'avg_score': round(sum(scores) / len(scores), 2) if scores else 0,
                'top_match_score': max(scores) if scores else 0,
            })

        if hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            matches = TeacherSchoolMatch.objects.filter(teacher=teacher)
            scores = list(matches.values_list('match_score', flat=True))
            return Response({
                'role': 'teacher',
                'total_matches': len(scores),
                'mutual_matches': matches.filter(status=MatchStatus.MUTUAL).count(),
                'school_interested': matches.filter(
                    status=MatchStatus.SCHOOL_INTERESTED).count(),
                'teacher_interested': matches.filter(
                    status=MatchStatus.TEACHER_INTERESTED).count(),
                'avg_score': round(sum(scores) / len(scores), 2) if scores else 0,
            })

        return Response(
            {'error': _('No profile found for this account.')},
            status=status.HTTP_400_BAD_REQUEST,
        )
