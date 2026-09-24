"""
Serializers for SkillPath Navigator API.
References: 
Lecture material 
https://www.django-rest-framework.org/api-guide/serializers/
"""

from rest_framework import serializers
from .models import JobPosting, Skill, JobSkillRequirement, Bookmark

class SkillSerializer(serializers.ModelSerializer):
    """
    Serializer for Skill model
    """

    class Meta:
        model = Skill
        fields = ['skill_name', 'category']

class SkillDemandSerializer(serializers.ModelSerializer):
    """
    Serializer for skills with demand statistics.
    
    Includes job_count field showing how many jobs require each skill.
    Used for ranking most demanded skills.
    """
    job_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Skill
        fields = ['skill_name', 'category', 'job_count']

class JobPostingSerializer(serializers.ModelSerializer):
    """
    Serializer for JobPosting model
    """
    skills = SkillSerializer(many=True, read_only=True)
    class Meta:
        model = JobPosting
        exclude = ['search_country'] 

class JobSkillRequirementSerializer(serializers.ModelSerializer):
    """
    Serializer for JobSkillRequirement model
    """

    class Meta:
        model = JobSkillRequirement
        fields = '__all__'

class JobMatchSerializer(serializers.ModelSerializer):
    """
    Serializer for jobs with skill match scoring.
    Used by:
    - Endpoint 3: /api/jobs/by-skills/ 
    """
    match_score = serializers.FloatField(read_only=True)
    required_skills_count = serializers.IntegerField(read_only=True)
    matched_skills_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            'job_link',
            'title',
            'company',
            'location',
            'city',
            'state_province',
            'country',
            'posted_date',
            'experience_level',
            'work_type',
            'match_score',
            'required_skills_count',
            'matched_skills_count'
        ]

class JobSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for job summaries.
    
    Used by:
    - Endpoint 4 (POST): /api/bookmarks/ (similar jobs recommendations)
    
    Omits skills for better performance when returning many jobs.
    Includes required_skills_count for quick assessment.
    """
    
    required_skills_count = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPosting
        fields = [
            'job_link',
            'title',
            'company',
            'location',
            'country',
            'experience_level',
            'work_type',
            'posted_date',
            'required_skills_count'
        ]
    
    def get_required_skills_count(self, obj):
        """Count skills required by this job."""
        return obj.skills.count()

class BookmarkSerializer(serializers.ModelSerializer):
    """
    Serializer for Bookmark model (CRUD operations).
    
    Used by:
    - Endpoint 4 (POST): /api/bookmarks/ - Create bookmark
    - Endpoint 5 (PUT): /api/bookmarks/<id>/ - Update bookmark
    - Endpoint 6 (DELETE): /api/bookmarks/<id>/ - Delete bookmark
    
    Handles both reading (GET) and writing (POST/PUT) operations.
    For POST: accepts job_link string, looks up JobPosting
    For GET: returns full job details via JobPostingSerializer
    """
    job_link = serializers.CharField(
        write_only=True, 
        required=False,
        help_text="Job URL from the dataset. Test with: https://uk.linkedin.com/jobs/view/junior-coder-at-e-careers-3793314768"
    )
    job = JobPostingSerializer(read_only=True)
    
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Personal notes about this job opportunity"
    )
    
    status = serializers.ChoiceField(
        choices=['interested', 'applied', 'interviewing', 'offered', 'rejected'],
        default='interested',
        help_text="Application status. Options: interested, applied, interviewing, offered, rejected"
    )

    class Meta:
        model = Bookmark
        fields = [
            'id',
            'job',
            'job_link',
            'notes',
            'status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        """
        Create bookmark from job_link.
        
        Expects: {"job_link": "https://...", "notes": "...", "status": "interested"}
        Looks up JobPosting by job_link and creates Bookmark.
        """
        job_link = validated_data.pop('job_link', None)

        if not job_link:
            raise serializers.ValidationError({
                'job_link': 'This field is required when creating a bookmark.'
            })
        
        # Look up job
        try: 
            job = JobPosting.objects.get(job_link=job_link)
        except JobPosting.DoesNotExist:
            raise serializers.ValidationError({
                'job_link': f'Job with link "{job_link}" not found.'
            })
        
        # Create bookmark
        bookmark = Bookmark.objects.create(job=job, **validated_data)
        return bookmark
     
    def update(self, instance, validated_data):
        """
        Update bookmark fields.
        Allows updating: notes, status
        Does not allow changing job (must delete and create new bookmark)
        """
        # Remove job_link if provided
        validated_data.pop('job_link', None)
        
        # Update allowed fields
        instance.notes = validated_data.get('notes', instance.notes)
        instance.status = validated_data.get('status', instance.status)
        instance.save()

        return instance 
    
class BookmarkListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for bookmark lists (GET /api/bookmarks/).
    
    Used by:
    - Endpoint 4 (GET): /api/bookmarks/ - List all bookmarks
    
    Shows job summary instead of full details for better performance.
    """

    job_title = serializers.CharField(source='job.title', read_only=True)
    job_company = serializers.CharField(source='job.company', read_only=True)
    job_location = serializers.CharField(source='job.location', read_only=True)

    class Meta:
        model = Bookmark
        fields = [
            'id',
            'job_title',
            'job_company',
            'job_location',
            'notes',
            'status',
            'created_at',
            'updated_at'
        ]