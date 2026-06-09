from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

from .models import School, SubjectNeed
from .serializers import (
    SchoolRegistrationSerializer, SchoolSerializer,
    SubjectNeedSerializer,
)


class SchoolRegisterView(APIView):
    """
    POST /api/schools/register/

    Creates a new school account together with one or more subject needs.
    Returns an authentication token on success.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SchoolRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            school = serializer.save()
            token, _created = Token.objects.get_or_create(user=school.user)
            return Response({
                'message': _('School registered successfully.'),
                'token': token.key,
                'school_id': school.id,
                'school_name': school.name,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SchoolLoginView(APIView):
    """
    POST /api/schools/login/

    Authenticates a school user and returns a token.
    Rejects credentials that belong to a teacher account.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user and hasattr(user, 'school_profile'):
            token, _created = Token.objects.get_or_create(user=user)
            school = user.school_profile
            return Response({
                'token': token.key,
                'school_id': school.id,
                'school_name': school.name,
                'district': school.district,
            })
        return Response(
            {'error': _('Invalid credentials or no school account found.')},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class SchoolProfileView(generics.RetrieveUpdateAPIView):
    """
    GET/PUT /api/schools/profile/

    Returns or updates the authenticated school's profile.
    """
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.school_profile


class SubjectNeedListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/schools/subject-needs/  – list the school's subject needs.
    POST /api/schools/subject-needs/  – add a new subject need.
    """
    serializer_class = SubjectNeedSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SubjectNeed.objects.filter(school=self.request.user.school_profile)

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school_profile)


class SubjectNeedDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/schools/subject-needs/<id>/

    Manage a single subject need belonging to the authenticated school.
    """
    serializer_class = SubjectNeedSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SubjectNeed.objects.filter(school=self.request.user.school_profile)


class SchoolListView(generics.ListAPIView):
    """
    GET /api/schools/list/

    Public listing of schools.  Supports filtering by district and level.
    Query parameters: district, level
    """
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = School.objects.all()
        district = self.request.query_params.get('district')
        level = self.request.query_params.get('level')
        if district:
            qs = qs.filter(district__icontains=district)
        if level:
            qs = qs.filter(education_level=level)
        return qs
