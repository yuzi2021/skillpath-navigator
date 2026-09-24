"""
Views for SkillPath Navigator
"""

from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import JobPosting, JobSkillRequirement, Skill

def index(request):
    """
    Display the landing page with API documentation.
    
    Template: index.html
    Context: None
    """
    return render(request, 'index.html')


@ensure_csrf_cookie
def app(request):
    """Render the consumer shell; analytics are fetched from the existing API."""
    counts = {
        'jobs': JobPosting.objects.count(),
        'skills': Skill.objects.count(),
        'relationships': JobSkillRequirement.objects.count(),
    }
    return render(request, 'app.html', {
        'counts': counts,
        'jobs_display': f"{counts['jobs']:,}",
        'skills_display': f"{counts['skills']:,}",
        'relationships_display': f"{counts['relationships']:,}",
    })

