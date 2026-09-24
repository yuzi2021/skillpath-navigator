"""
URL configuration for SkillPath Navigator API endpoints.

Routes API requests to endpoint functions in api.py
"""

from django.urls import path
from . import api

urlpatterns = [
path('skills/most-demanded/', api.skills_most_demanded, name='skills-most-demanded'),
path('skills/for-role/', api.skills_for_role, name='skills-for-role'),
path('jobs/by-skills/', api.jobs_by_skills, name='jobs-by-skills'),
path('skills/combinations/', api.skill_combinations, name='skill-combinations'),
path('bookmarks/', api.BookmarkListCreateView.as_view(), name='bookmark-list-create'),
path('bookmarks/<int:pk>/', api.BookmarkDetailView.as_view(), name='bookmark-detail'),
]
 