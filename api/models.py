"""
Database models for SkillPath Navigator API.
Models:
- JobPosting: Entry-level software engineering jobs
- Skill: Technical and  soft skills required by jobs
- JobSkillRequirement: Many-to-many relationship between jobs and skills
- Bookmark: User bookmark for job postings of interest.

References: 
lecture material
"""
from django.db import models

class JobPosting(models.Model):
    """
    Represents an entry-level software engineering job posting from LinkedIn.
    
    Each job has a unique URL and contains information about the position,
    company, location, and required skills.
    """

    # Primary key - LinkedIn job URL
    job_link = models.URLField(
        max_length=500, 
        primary_key = True, 
        help_text="Unique LinkedIn job URL"
    )
    # Job information
    title = models.CharField(max_length=500, help_text="Job title")
    company = models.CharField(max_length=200, help_text="Company name")

    # Location details
    location = models.CharField(max_length=200, help_text="Full location string")
    city = models.CharField(max_length=100, blank=True, help_text="City name")
    state_province = models.CharField(max_length=100, blank=True, help_text="State or province")
    country = models.CharField(max_length=100, help_text="Country name")
    
    # Job metadata
    posted_date = models.DateField(help_text="Date job was posted")
    experience_level = models.CharField(max_length=50, help_text="Entry level")
    work_type = models.CharField(max_length=50, help_text="Onsite, Remote, Hybrid, Unknown")
    search_country = models.CharField(max_length=100, help_text="Country used in search")

    # Many-to-many relationship with Skills
    skills = models.ManyToManyField(
        'Skill',
        through='JobSkillRequirement',
        related_name='jobs',
        help_text='Skills required for this job'
    )

    class Meta:
        ordering = ['-posted_date']
        verbose_name = "Job Posting"
        verbose_name_plural = "Job Postings"
    
    def __str__(self):
        return f"{self.title} at {self.company}"



class Skill(models.Model):
    """
    Represents a technical or soft skill required by jobs.
    
    Skills are categorized (LANGUAGE, FRAMEWORK, DATABASE, etc.) to enable filtering and analysis by skill type.
    """    

    skill_name = models.CharField(
        max_length=200, 
        primary_key = True, 
        help_text="Unique skill name"
    )
    
    category = models.CharField(
        max_length=50, 
        help_text="Skill category: LANGUAGE, FRAMEWORK, DATABASE, etc."
    )

    class Meta:
        ordering = ['skill_name']
        verbose_name = "Skill"
        verbose_name_plural = "Skills"

    def __str__(self):
        return f"{self.skill_name} ({self.category})"

class JobSkillRequirement(models.Model):
    """
    Links job postings to their required skills (many-to-many relationship).
    
    This is the "through" model that creates the junction table between
    JobPosting and Skill. Each record represents one skill required by one job.
    """

    job = models.ForeignKey(
        JobPosting, 
        on_delete=models.CASCADE,
        help_text="Job posting requiring this skill" 
    )
        
    skill = models.ForeignKey(
        Skill, 
        on_delete=models.CASCADE,
        help_text="Skill required by this job"

    )

    class Meta:
        unique_together = ("job", "skill")
        verbose_name = "Job Skill Requirement"
        verbose_name_plural = "Job Skill Requirements"
    
    def __str__(self):
        return f"{self.job.title} requires {self.skill.skill_name}"

class Bookmark(models.Model):
    """ 
    User bookmark for job postings of interest. 
    Allows bootcamp graduates to save jobs they want to apply to, 
    track application status, and receive personalized recommendations. 
    This demonstrates CREATE, UPDATE, DELETE operations in the API. 
    Attributes: 
        id: Auto-generated primary key 
        job: Foreign key to JobPosting 
        notes: User's personal notes about the job 
        status: Application tracking status 
        created_at: When bookmark was created 
    """
    job = models.ForeignKey(
        JobPosting, 
        on_delete=models.CASCADE,
        help_text="Job posting being bookmarked" 
        )

    notes = models.TextField(
        blank=True,
        default='', 
        help_text="User's personal notes about this job (why interested, preparation needed, etc.)"
        )
    
    STATUS_CHOICES = [ 
    ('interested', 'Interested - Want to Apply'), 
    ('researching', 'Researching - Learning About Company'), 
    ('preparing', 'Preparing - Updating Resume/Portfolio'), 
    ('applied', 'Applied - Waiting for Response'), 
    ('interviewing', 'Interviewing - In Process'), 
    ('offer', 'Offer Received'), 
    ('rejected', 'Rejected'), 
    ('withdrawn', 'Withdrawn - No Longer Interested'), 
    ]

    status = models.CharField( 
    max_length=20, 
    choices=STATUS_CHOICES, 
    default='interested', 
    help_text="Current status in application process" 
    )  
    created_at = models.DateTimeField(
        auto_now_add=True, 
        help_text="When bookmark was created" 
    )
    updated_at = models.DateTimeField( 
        auto_now=True, 
        help_text="When bookmark was last modified" 
    )

    class Meta: 
        ordering = ['-created_at']  # Newest first 
        verbose_name = "Job Bookmark" 
        verbose_name_plural = "Job Bookmarks" 

    def __str__(self): 
        return f"Bookmark: {self.job.title} at {self.job.company} ({self.status})"