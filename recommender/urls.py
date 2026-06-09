from django.urls import path
from . import views

urlpatterns = [
    path('run/', views.RunRecommendationView.as_view(), name='run-recommendation'),
    path('refresh/', views.RefreshMatchesView.as_view(), name='refresh-matches'),
    path('school-matches/', views.SchoolMatchesView.as_view(), name='school-matches'),
    path('teacher-matches/', views.TeacherMatchesView.as_view(), name='teacher-matches'),
    path('school-match/<int:match_id>/status/', views.SchoolUpdateMatchStatusView.as_view(), name='school-match-status'),
    path('teacher-match/<int:match_id>/status/', views.TeacherUpdateMatchStatusView.as_view(), name='teacher-match-status'),
    path('stats/', views.MatchStatsView.as_view(), name='match-stats'),
]
