"""
DRF API endpoints for SkillPath Navigator.

Following the lecture pattern: views.py handles traditional HTML rendering,
while api.py handles RESTful JSON API endpoints.

Endpoints serve bootcamp graduates seeking entry-level software engineering jobs.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response 
from rest_framework import generics, status
from django.db.models import Count, Q
from .models import Skill, JobPosting, JobSkillRequirement, Bookmark
from .serializers import (
    SkillSerializer, 
    JobPostingSerializer, 
    SkillDemandSerializer,
    JobMatchSerializer,
    JobSummarySerializer,
    BookmarkSerializer,
    BookmarkListSerializer
)
from .constants import(
    ROLE_KEYWORDS,
    normalize_role_query,
    get_keywords_for_role,
    USER_ROLE_CATEGORIES
)

# ============================================================================
# ENDPOINT 1: Most Demanded Skills
# ============================================================================

@api_view(['GET'])
def skills_most_demanded(request):
    """
    Return top 20 most demanded skills across all entry-level jobs.
    
    Endpoint helps bootcamp graduates prioritize what skills to learn first
    by showing which competencies appear most frequently in job requirements.
    
    Returns:
        Response: JSON list of skills with job_count, ordered by demand
        
    Example:
        GET /api/skills/most-demanded/
        Returns: [{"skill_name": "Python", "category": "LANGUAGE", "job_count": 156}, ...]
    """
    try:
        # Get all skills and annotate with job count
        skills = Skill.objects.annotate(
            job_count=Count('jobskillrequirement')
        ).order_by('-job_count')[:20]
        
        # Serialize and return
        serializer = SkillDemandSerializer(skills, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        # Log the actual error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in skills_most_demanded: {str(e)}")
        
        return Response(
            {'error': 'Unable to fetch skills data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ============================================================================
# ENDPOINT 2: Skills required for a specific role
# ============================================================================

@api_view(['GET'])
def skills_for_role(request):
    """
    Return skills commonly required for a specific entry-level role.
    
    Complex keyword matching logic requires function-based view.
    
    Query Parameters:
        role (required): backend, frontend, fullstack, data, devops, mobile, qa, software
    
    Query Processing:
        1. Normalize: "Backend Developer" → "backend"
        2. Keywords: Get search terms for role
        3. Match: Build Q objects for OR queries
        4. Filter: Find matching jobs
        5. Aggregate: Count skills in those jobs
        6. Rank: Order by frequency
    
    Returns:
        Response: JSON with role info and top skills
        
    Errors:
        400: Role parameter missing or invalid
    
    Example:
        GET /api/skills/for-role/?role=backend
        
        Response (200 OK):
        {
            "role": "backend",
            "matching_jobs_count": 89,
            "top_skills": [...]
        }

    References:
    Django QuerySets - Basic filtering (.filter(), .exclude())
    Q Objects - Complex OR/AND queries
    Relationship Traversal - Double underscore (__) following ForeignKeys
    Aggregation - Count, Sum, Avg with .annotate()
    Conditional Aggregation - Using filter= inside Count()
    QuerySet Optimization - distinct, select_related, prefetch_related
    """
    role_query = request.query_params.get('role', '').strip()

    if not role_query:
        return Response(
            {'error': 'Role parameter is required. Example: ?role=backend'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    role_key = normalize_role_query(role_query)
    
    if not role_key:
        valid_roles = ', '.join(ROLE_KEYWORDS.keys())
        return Response(
            {
                'error':f"Invalid role '{role_query}'. Valid roles: {valid_roles}", 
                'hint':'Try: backend, frontend, fullstack, data, devops, mobile, qa, software'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    keywords = get_keywords_for_role(role_key)

    title_query = Q()
    for keyword in keywords:
        title_query |= Q(title__icontains=keyword)
    
    matching_jobs = JobPosting.objects.filter(title_query)
    matching_jobs_count = matching_jobs.count()
    skills = Skill.objects.filter(
        jobskillrequirement__job__in=matching_jobs
    ).annotate(
        job_count=Count('jobskillrequirement',
                        filter=Q(jobskillrequirement__job__in=matching_jobs),
                        distinct=True)
    ).order_by('-job_count')[:20]

    serializer = SkillDemandSerializer(skills, many=True)

    return Response({
        'role': role_key,
        'query': role_query,
        'matching_jobs_count': matching_jobs_count,
        'top_skills': serializer.data
    })

# ============================================================================
# ENDPOINT 3: Jobs matching skills
# ============================================================================

@api_view(['GET'])
def jobs_by_skills(request):
    """
    Find entry-level jobs matching users' current skills.
    
    Uses case-insensitive matching so 'Python', 'python', and 'PYTHON' 
    all match the same skill.
    
    Query Parameters: 
        skills (required): Comma-separated list (e.g., Python,Django,SQL) 
    
    Query Processing: 
        1. Parse: Split comma-separated skills 
        2. Normalize: Convert to lowercase for matching
        3. Find: Jobs requiring at least one skill (case-insensitive)
        4. Calculate: Match score for each job 
        5. Rank: Sort by match percentage 
        6. Limit: Top 50 results 
    
    Returns: 
        Response: JSON with matching jobs and scores 
        
    Errors: 
        400: Skills parameter missing or empty 
    
    Example: 
        GET /api/jobs/by-skills/?skills=Python,Django,SQL 
        
        Response (200 OK): 
        { 
            "skills_searched": ["Python", "Django", "SQL"], 
            "total_matching_jobs": 42, 
            "jobs": [ 
                { 
                    "title": "Backend Developer", 
                    "match_score": 75.0, 
                    "matched_skills_count": 3, 
                    "required_skills_count": 4 
                } 
            ] 
        } 
    """
    # Get and validate skills parameter
    skills_param = request.query_params.get('skills', '').strip()
    
    if not skills_param:
        return Response(
            {
                'error': 'Skills parameter is required',
                'example': '/api/jobs/by-skills/?skills=Python,Django,SQL'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Parse comma-separated skills
    user_skills = [s.strip() for s in skills_param.split(',') if s.strip()]
    
    if not user_skills:
        return Response(
            {'error': 'At least one valid skill must be provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Build case-insensitive query using Q objects
    # This matches 'Python', 'python', 'PYTHON', etc.
    skill_query = Q()
    for skill in user_skills:
        skill_query |= Q(skills__skill_name__iexact=skill)
    
    # Find jobs that require at least one of user's skills (case-insensitive)
    matching_jobs = JobPosting.objects.filter(skill_query).distinct()
    
    # Calculate match scores for each job
    jobs_with_scores = []
    
    for job in matching_jobs:
        # Get all skills required by this job
        required_skills = job.skills.all()
        required_count = required_skills.count()
        
        # Skip jobs with no skills listed
        if required_count == 0:
            continue
        
        # Count how many of user's skills match job requirements (case-insensitive)
        # Build case-insensitive filter for user's skills
        user_skill_filter = Q()
        for skill in user_skills:
            user_skill_filter |= Q(skill_name__iexact=skill)
        
        matched_count = required_skills.filter(user_skill_filter).count()
        
        # Calculate match percentage
        match_score = (matched_count / required_count) * 100
        
        # Add calculated fields to job object for serialization
        job.match_score = round(match_score, 1)
        job.required_skills_count = required_count
        job.matched_skills_count = matched_count
        
        jobs_with_scores.append(job)
    
    # Sort by match score (highest first)
    jobs_with_scores.sort(key=lambda x: x.match_score, reverse=True)
    
    # Limit to top 50 results
    jobs_with_scores = jobs_with_scores[:50]
    
    # Serialize and return
    serializer = JobMatchSerializer(jobs_with_scores, many=True)
    
    return Response({
        'skills_searched': user_skills,
        'total_matching_jobs': len(jobs_with_scores),
        'jobs': serializer.data
    })

# ============================================================================
# ENDPOINT 4: skill combinations
# ============================================================================

@api_view(['GET'])
def skill_combinations(request):
    """
    Analyze which skills commonly appear together in job postings.
    
    For bootcamp graduates planning their learning path, understanding which
    skills pair well together is crucial. This endpoint finds jobs requiring
    a specific skill, then analyzes what OTHER skills those jobs also require,
    ranked by co-occurrence frequency.
    
    Query Parameters:
        skill (required): Base skill to analyze (e.g., "Python", "JavaScript")
    
    Query Processing:
        1. Validate: Check skill parameter provided and exists
        2. Find: Jobs requiring the base skill (case-insensitive)
        3. Analyze: What OTHER skills do those jobs require?
        4. Count: How often each complementary skill appears
        5. Rank: Order by co-occurrence percentage
        6. Limit: Top 20 most common pairings
    
    Returns:
        Response (200 OK): JSON with base skill and commonly paired skills
            {
                "base_skill": "Python",
                "category": "LANGUAGE",
                "total_jobs_with_skill": 156,
                "commonly_paired_skills": [
                    {
                        "skill_name": "SQL",
                        "category": "DATABASE",
                        "co_occurrence_count": 98,
                        "percentage": 62.8,
                        "recommendation": "Highly recommended - appears in 63% of Python jobs"
                    },
                    {
                        "skill_name": "Git",
                        "category": "TOOL",
                        "co_occurrence_count": 87,
                        "percentage": 55.8,
                        "recommendation": "Highly recommended - appears in 56% of Python jobs"
                    }
                ]
            }
    
    Errors:
        400: Skill parameter missing
        404: Skill not found in database
    
    Example:
        GET /api/skills/combinations/?skill=Python
        
        Shows that Python jobs commonly also require SQL, Git, Django, AWS, etc.
        Helps user decide: "I'm learning Python, what should I learn next?"
    
    Use Cases:
        - Bootcamp graduate learning Python wants to know complementary skills
        - Career changer planning learning roadmap
        - Understanding skill ecosystems (backend stack, frontend stack, etc.)
    
    References:
        - Django ORM filtering with case-insensitive lookups
        - Relationship traversal across many-to-many
        - Aggregation with Count()
        - Excluding self from results
        - Percentage calculations
    """
    
    # Get and validate skill parameter
    skill_param = request.query_params.get('skill', '').strip()
    
    if not skill_param:
        return Response(
            {
                'error': 'Skill parameter is required',
                'example': '/api/skills/combinations/?skill=Python',
                'hint': 'Provide a skill name to see which skills commonly pair with it'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Find the base skill (case-insensitive)
    try:
        base_skill = Skill.objects.get(skill_name__iexact=skill_param)
    except Skill.DoesNotExist:
        # Try partial match if exact match fails
        similar_skills = Skill.objects.filter(
            skill_name__icontains=skill_param
        )[:5]
        
        if similar_skills.exists():
            suggestions = [s.skill_name for s in similar_skills]
            return Response(
                {
                    'error': f'Skill "{skill_param}" not found',
                    'suggestions': suggestions,
                    'hint': 'Did you mean one of these?'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        else:
            return Response(
                {
                    'error': f'Skill "{skill_param}" not found in database',
                    'hint': 'Check spelling or try GET /api/skills/most-demanded/ to see available skills'
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Find all jobs requiring this skill
    jobs_with_base_skill = JobPosting.objects.filter(
        skills=base_skill
    )
    
    total_jobs_count = jobs_with_base_skill.count()
    
    if total_jobs_count == 0:
        return Response(
            {
                'base_skill': base_skill.skill_name,
                'category': base_skill.category,
                'total_jobs_with_skill': 0,
                'message': f'No jobs found requiring {base_skill.skill_name}',
                'commonly_paired_skills': []
            }
        )
    
    # Find other skills required by those same jobs
    # Exclude the base skill itself from results
    paired_skills = Skill.objects.filter(
        jobs__in=jobs_with_base_skill
    ).exclude(
        skill_name=base_skill.skill_name 
    ).annotate(
        co_occurrence_count=Count(
            'jobs',
            filter=Q(jobs__in=jobs_with_base_skill),
            distinct=True
        )
    ).order_by('-co_occurrence_count')[:20]
    
    # Calculate percentages and add recommendations
    paired_skills_data = []
    for skill in paired_skills:
        percentage = (skill.co_occurrence_count / total_jobs_count) * 100
        
        # Generate recommendation based on percentage
        if percentage >= 60:
            recommendation = f"Highly recommended - appears in {percentage:.0f}% of {base_skill.skill_name} jobs"
            priority = "HIGH"
        elif percentage >= 30:
            recommendation = f"Recommended - appears in {percentage:.0f}% of {base_skill.skill_name} jobs"
            priority = "MEDIUM"
        else:
            recommendation = f"Optional - appears in {percentage:.0f}% of {base_skill.skill_name} jobs"
            priority = "LOW"
        
        paired_skills_data.append({
            'skill_name': skill.skill_name,
            'category': skill.category,
            'co_occurrence_count': skill.co_occurrence_count,
            'percentage': round(percentage, 1),
            'priority': priority,
            'recommendation': recommendation
        })
    
    # Build response
    return Response({
        'base_skill': base_skill.skill_name,
        'category': base_skill.category,
        'total_jobs_with_skill': total_jobs_count,
        'analysis': f'Analyzed {total_jobs_count} jobs requiring {base_skill.skill_name}',
        'commonly_paired_skills': paired_skills_data,
        'total_paired_skills': len(paired_skills_data),
        'learning_tip': f'If you know {base_skill.skill_name}, focus on HIGH priority skills first for maximum job opportunities.'
    })

# ============================================================================
# ENDPOINT 5: create and list bookmark
# ============================================================================
class BookmarkListCreateView(generics.ListCreateAPIView):
    """
    Combined view for bookmark collection operations.
    
    Handles both:
    - GET  /api/bookmarks/  - List all bookmarks with statistics
    - POST /api/bookmarks/  - Create new bookmark with similar job recommendations
    
    This is the CORRECT way to handle a collection endpoint in REST.
    One URL, multiple HTTP methods.
    """
    queryset = Bookmark.objects.all()
    
    def get_serializer_class(self):
        """
        Use different serializers for different HTTP methods.
        
        - POST (create): BookmarkSerializer (accepts job_link string)
        - GET (list): BookmarkListSerializer (lightweight summary)
        """
        if self.request.method == 'POST':
            return BookmarkSerializer
        return BookmarkListSerializer
    
    def get_queryset(self):
        """
        Override to add ordering and optional filtering.
        
        Orders by newest first. Optionally filter by status.
        """
        queryset = Bookmark.objects.all().order_by('-created_at')
        
        # Optional status filter
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Override create to add similar job recommendations.
        
        After creating bookmark, finds 3 similar jobs based on skill overlap
        and returns them as recommendations.
        """
        # Call parent create (handles validation and saving)
        response = super().create(request, *args, **kwargs)
        
        # Get the created bookmark
        bookmark_id = response.data.get('id')
        bookmark = Bookmark.objects.get(id=bookmark_id)
        
        # Find similar jobs based on skill overlap
        bookmarked_job = bookmark.job
        bookmarked_skills = bookmarked_job.skills.all()
        
        similar_jobs = JobPosting.objects.filter(
            skills__in=bookmarked_skills
        ).exclude(
            job_link=bookmarked_job.job_link
        ).distinct().order_by('?')[:3]
        
        # Serialize similar jobs
        similar_serializer = JobSummarySerializer(similar_jobs, many=True)
        
        # Enhance response with recommendations
        response.data = {
            'bookmark': response.data,
            'similar_jobs': similar_serializer.data,
            'similar_jobs_count': len(similar_jobs),
            'message': f'Bookmark created! Here are {len(similar_jobs)} similar positions you might like.'
        }
        
        return response
    
    
    def list(self, request, *args, **kwargs):
        """
        Override list to add application statistics.
        
        Returns bookmark list plus overall progress statistics grouped
        by application status.
        """
        # Get standard list response
        response = super().list(request, *args, **kwargs)
        
        # Calculate statistics across ALL bookmarks (not just filtered)
        all_bookmarks = Bookmark.objects.all()
        
        statistics = {
            'total': all_bookmarks.count(),
            'interested': all_bookmarks.filter(status='interested').count(),
            'applied': all_bookmarks.filter(status='applied').count(),
            'interviewing': all_bookmarks.filter(status='interviewing').count(),
            'rejected': all_bookmarks.filter(status='rejected').count()
        }
        
        # Add statistics to response
        response.data['statistics'] = statistics
        
        return response

# ============================================================================
# ENDPOINT 6: Bookmark Detail/Update/Delete (GET/PUT/PATCH/DELETE)
# ============================================================================

class BookmarkDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific bookmark.
    
    Combines all detail operations (GET/PUT/PATCH/DELETE) in one view,
    following RESTful design principles. This is the standard DRF pattern
    for resource detail endpoints.
    
    URL: /api/bookmarks/<id>/
    
    Supported Methods:
        - GET: Retrieve full bookmark details
        - PUT: Full update (all fields required)
        - PATCH: Partial update (only changed fields)
        - DELETE: Remove bookmark
    
    -------------------------------------------------------------------------
    GET - Retrieve Bookmark
    -------------------------------------------------------------------------
    
    Returns complete bookmark details including full job information with
    all required skills. Helps users review bookmarked positions.
    
    Returns:
        Response (200 OK): JSON with full bookmark details
            {
                "id": 1,
                "job": {
                    "job_link": "...",
                    "title": "Backend Developer",
                    "company": "Google",
                    "skills": [...],
                    "location": "Remote",
                    ...
                },
                "notes": "Great culture",
                "status": "interested",
                "created_at": "2024-12-27T10:30:00Z",
                "updated_at": "2024-12-27T10:30:00Z"
            }
    
    Example:
        GET /api/bookmarks/1/
    
    -------------------------------------------------------------------------
    PUT/PATCH - Update Bookmark
    -------------------------------------------------------------------------
    
    Allows users to update notes or application status as they progress
    through the job search process. After updating, returns application
    progress statistics.
    
    Request Body (PATCH - partial update):
        {
            "notes": "Applied via company website",
            "status": "applied"
        }
    
    Request Body (PUT - full update):
        {
            "notes": "Updated notes",
            "status": "applied"
        }
    
    Note: Cannot change job after bookmark created. To bookmark different
          job, delete this bookmark and create new one.
    
    Returns:
        Response (200 OK): JSON with updated bookmark and statistics
            {
                "bookmark": {
                    "id": 1,
                    "notes": "Applied via company website",
                    "status": "applied",
                    "updated_at": "2024-12-27T11:45:00Z"
                },
                "application_stats": {
                    "total_bookmarks": 5,
                    "interested": 2,
                    "applied": 2,
                    "interviewing": 1,
                    "rejected": 0
                },
                "message": "Bookmark updated! You've now applied to 2 positions."
            }
    
    Example:
        PATCH /api/bookmarks/1/
        Body: {"status": "applied"}
    
    -------------------------------------------------------------------------
    DELETE - Remove Bookmark
    -------------------------------------------------------------------------
    
    Removes bookmark from saved jobs. Returns informative response showing
    what was deleted and remaining bookmark statistics.
    
    Returns:
        Response (200 OK): JSON with deletion confirmation
            {
                "message": "Bookmark deleted successfully",
                "deleted_job": {
                    "title": "Backend Developer",
                    "company": "Google"
                },
                "remaining_bookmarks": 4,
                "status_breakdown": {
                    "interested": 2,
                    "applied": 1,
                    "interviewing": 1,
                    "rejected": 0
                },
                "tip": "Keep exploring! Check /api/skills/most-demanded/ for in-demand skills."
            }
    
    Example:
        DELETE /api/bookmarks/1/
    
    References:
        - generics.RetrieveUpdateDestroyAPIView - DRF combined generic view
        - Partial updates - PATCH vs PUT difference
        - Custom destroy - Override for informative delete response
    """
    queryset = Bookmark.objects.all()
    serializer_class = BookmarkSerializer

    def update(self, request, *args, **kwargs):
        """
        Override update to add application progress statistics.
        
        After updating bookmark status, provides user with overview of
        their overall application progress across all bookmarks.
        """
        # perform the update (handles both PUT and PATCH)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial = partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # calculate application statistics 
        all_bookmarks = Bookmark.objects.all()
        total_count = all_bookmarks.count()
        status_breakdown = {
                    'interested': all_bookmarks.filter(status='interested').count(),
                    'applied': all_bookmarks.filter(status='applied').count(),
                    'interviewing': all_bookmarks.filter(status='interviewing').count(),
                    'rejected': all_bookmarks.filter(status='rejected').count()
        }

        # Create message based on new status
        new_status = serializer.data.get('status')
        if new_status == 'applied':
            message = f"Bookmark updated! You've now applied to {status_breakdown['applied']} positions."
        elif new_status == 'interviewing':
            message = f"Great progress! You have {status_breakdown['interviewing']} interview(s) scheduled."
        elif new_status == 'rejected':
            message = "Don't give up! Each rejection brings you closer to the right opportunity."
        else:
            message = "Bookmark updated successfully."
        
        # response with statistics
        return Response({
            'bookmark': serializer.data,
            'application_stats':{
                'total_bookmarks': total_count,
                **status_breakdown
            },
            'message': message
        }) 
    
    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to return informative response.
        
        Instead of standard 204 No Content, returns 200 OK with information
        about what was deleted and remaining bookmarks. Improves UX by
        maintaining context after deletion.
        """
        # get bookmark info before deleting
        instance = self.get_object()
        deleted_job_title = instance.job.title
        deleted_job_company = instance.job.company

        # delete the bookmark
        self.perform_destroy(instance)

        # calculate remaining bookmark statistics
        remaining_bookmarks = Bookmark.objects.all()
        remaining_count = remaining_bookmarks.count()

        status_breakdown = {
            'interested': remaining_bookmarks.filter(status='interested').count(),
            'applied': remaining_bookmarks.filter(status='applied').count(),
            'interviewing': remaining_bookmarks.filter(status='interviewing').count(),
            'rejected': remaining_bookmarks.filter(status='rejected').count()
        }

        # provide helpful tip if no bookmarks remain
        tip = None 
        if remaining_count == 0:
            tip  = "Keep exploring! Check /api/skills/most-demanded/ for in-demand skills."
        
        return Response({
            'message': 'Bookmark deleted successfully',
            'deleted_job': {
                'title': deleted_job_title,
                'company': deleted_job_company
            },
            'remaining_bookmarks': remaining_count,
            'status_breakdown': status_breakdown,
            'tip': tip
        }, status=status.HTTP_200_OK)
    
"""

REFERENCES AND LEARNING RESOURCES:
===================================

Django ORM Documentation:
-------------------------
1. QuerySet API Reference
   https://docs.djangoproject.com/en/5.0/ref/models/querysets/
   - Used for: .filter(), .exclude(), .annotate(), .order_by(), .distinct()
   
2. Making Queries
   https://docs.djangoproject.com/en/5.0/topics/db/queries/
   - Used for: Relationship traversal, lookups (icontains, iexact)
   
3. Complex Lookups with Q Objects
   https://docs.djangoproject.com/en/5.0/topics/db/queries/#complex-lookups-with-q-objects
   - Used for: Building OR conditions in skills_for_role and jobs_by_skills
   
4. Aggregation
   https://docs.djangoproject.com/en/5.0/topics/db/aggregation/
   - Used for: Count(), conditional aggregation with filter parameter

Django REST Framework Documentation:
------------------------------------
5. Function Based Views
   https://www.django-rest-framework.org/api-guide/views/#function-based-views
   - Used for: @api_view decorator in endpoints 1-4
   
6. Generic Views
   https://www.django-rest-framework.org/api-guide/generic-views/
   - Used for: ListCreateAPIView, RetrieveUpdateDestroyAPIView (endpoints 5-6)
   
7. Serializers
   https://www.django-rest-framework.org/api-guide/serializers/
   - Used for: ModelSerializer, nested serialization, validation
   
8. Request and Response
   https://www.django-rest-framework.org/api-guide/requests/
   - Used for: request.query_params, Response() object
   
9. Status Codes
   https://www.django-rest-framework.org/api-guide/status-codes/
   - Used for: HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

RESTful API Design Principles:
------------------------------
10. REST API Tutorial (Mozilla)
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
    - Principles: GET (read), POST (create), PATCH (partial update), DELETE (remove)

11. Richardson Maturity Model
    https://martinfowler.com/articles/richardsonMaturityModel.html
    - Level 2 REST achieved through proper HTTP verb usage and status codes

Course Materials:
----------------
12. CM3035 Advanced Web Development
    University of London, Topics 1-5
    - Django models, views, serializers, REST principles
    
13. CM3035 Topic 4: Testing and Debugging
    - Unit testing patterns applied in tests.py

Academic References:
-------------------
14. Fielding, R. T. (2000). Architectural Styles and the Design of Network-based 
    Software Architectures. Doctoral dissertation, University of California, Irvine.
    - Original REST architectural style definition

15. Masse, M. (2011). REST API Design Rulebook. O'Reilly Media.
    - Resource naming, URI design patterns followed in endpoint structure

Code Pattern References:
-----------------------
16. Django Design Patterns and Best Practices
    Used patterns:
    - Fat models, thin views
    - DRY principle (get_or_create in data loading)
    - Separation of concerns (api.py vs views.py)
"""