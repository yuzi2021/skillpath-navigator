"""
URL configuration for skillpath project.
references
https://www.youtube.com/watch?v=fbIFdWj8PsY
https://docs.djangoproject.com/en/5.1/topics/http/urls/

"""
from django.contrib import admin
from django.urls import path, include
from api import views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger configuration
schema_view = get_schema_view(
    openapi.Info(
        title="SkillPath Navigator API",
        default_version='v1',
        description="RESTful API analyzing entry-level software engineering jobs",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc'),
    path('app/', views.app, name='app'),
    path('', views.index, name='index'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
