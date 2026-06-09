from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schools/', include('schools.urls')),
    path('api/teachers/', include('teachers.urls')),
    path('api/recommend/', include('recommender.urls')),
    
    # Generic token endpoint – works for any User (school, teacher, or admin)
    path('api/auth/token/', obtain_auth_token, name='api-token-auth'),
]
