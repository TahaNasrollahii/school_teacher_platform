from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.TeacherRegisterView.as_view(), name='teacher-register'),
    path('login/', views.TeacherLoginView.as_view(), name='teacher-login'),
    path('profile/', views.TeacherProfileView.as_view(), name='teacher-profile'),
    path('subjects/', views.TeachingSubjectListCreateView.as_view(), name='teaching-subjects'),
    path('subjects/<int:pk>/', views.TeachingSubjectDetailView.as_view(), name='teaching-subject-detail'),
    path('list/', views.TeacherListView.as_view(), name='teacher-list'),
]
