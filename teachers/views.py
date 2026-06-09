from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

from .models import Teacher, TeachingSubject
from .serializers import (
    TeacherRegistrationSerializer, TeacherSerializer,
    TeachingSubjectSerializer,
)


class TeacherRegisterView(APIView):
    """
    POST /api/teachers/register/

    Creates a new teacher account with one or more teaching subjects.
    Returns an authentication token on success.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TeacherRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            teacher = serializer.save()
            token, _created = Token.objects.get_or_create(user=teacher.user)
            return Response({
                'message': _('Teacher registered successfully.'),
                'token': token.key,
                'teacher_id': teacher.id,
                'full_name': teacher.full_name,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeacherLoginView(APIView):
    """
    POST /api/teachers/login/

    Authenticates a teacher user and returns a token.
    Rejects credentials that belong to a school account.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user and hasattr(user, 'teacher_profile'):
            token, _created = Token.objects.get_or_create(user=user)
            teacher = user.teacher_profile
            return Response({
                'token': token.key,
                'teacher_id': teacher.id,
                'full_name': teacher.full_name,
                'district': teacher.district,
            })
        return Response(
            {'error': _('Invalid credentials or no teacher account found.')},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class TeacherProfileView(generics.RetrieveUpdateAPIView):
    """
    GET/PUT /api/teachers/profile/

    Returns or updates the authenticated teacher's profile.
    """
    serializer_class = TeacherSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.teacher_profile


class TeachingSubjectListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/teachers/subjects/  – list the teacher's teaching subjects.
    POST /api/teachers/subjects/  – add a new teaching subject.
    """
    serializer_class = TeachingSubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TeachingSubject.objects.filter(teacher=self.request.user.teacher_profile)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user.teacher_profile)


class TeachingSubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/teachers/subjects/<id>/

    Manage a single teaching subject belonging to the authenticated teacher.
    """
    serializer_class = TeachingSubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TeachingSubject.objects.filter(teacher=self.request.user.teacher_profile)


class TeacherListView(generics.ListAPIView):
    """
    GET /api/teachers/list/

    Public listing of available teachers.
    Query parameters: district, level, subject
    """
    serializer_class = TeacherSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Teacher.objects.filter(is_available=True)
        district = self.request.query_params.get('district')
        level = self.request.query_params.get('level')
        subject = self.request.query_params.get('subject')
        if district:
            qs = qs.filter(district__icontains=district)
        if level:
            qs = qs.filter(education_level=level)
        if subject:
            qs = qs.filter(subjects__subject_name__icontains=subject).distinct()
        return qs
