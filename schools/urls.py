from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.SchoolRegisterView.as_view(), name='school-register'),
    path('login/', views.SchoolLoginView.as_view(), name='school-login'),
    path('profile/', views.SchoolProfileView.as_view(), name='school-profile'),
    path('subject-needs/', views.SubjectNeedListCreateView.as_view(), name='subject-needs'),
    path('subject-needs/<int:pk>/', views.SubjectNeedDetailView.as_view(), name='subject-need-detail'),
    path('list/', views.SchoolListView.as_view(), name='school-list'),
]
