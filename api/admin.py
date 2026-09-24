"""
Admin configuration for SkillPath Navigator API.

Registers all models with customized admin interfaces for easy data management.

References:
- CM3035 lecture material
- https://docs.djangoproject.com/en/5.0/ref/contrib/admin/
"""

from django.contrib import admin
from .models import JobPosting, Skill, JobSkillRequirement, Bookmark


# ============================================================================
# JOB POSTING ADMIN
# ============================================================================

@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    """Admin interface for JobPosting model."""
    
    list_display = ['title', 'company', 'country', 'experience_level', 'posted_date']
    list_filter = ['work_type', 'country', 'experience_level']
    search_fields = ['title', 'company', 'location']
    date_hierarchy = 'posted_date'
    ordering = ['-posted_date']
    
    # Show skills in detail view
    readonly_fields = ['job_link']
    
    fieldsets = (
        ('Job Information', {
            'fields': ('job_link', 'title', 'company')
        }),
        ('Location Details', {
            'fields': ('location', 'city', 'state_province', 'country')
        }),
        ('Job Details', {
            'fields': ('experience_level', 'work_type', 'posted_date')
        }),
    )


# ============================================================================
# SKILL ADMIN
# ============================================================================

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Admin interface for Skill model."""
    
    list_display = ['skill_name', 'category', 'job_count']
    list_filter = ['category']
    search_fields = ['skill_name']
    ordering = ['skill_name']
    
    def job_count(self, obj):
        """Display number of jobs requiring this skill."""
        return obj.jobs.count()
    job_count.short_description = 'Jobs Requiring Skill'


# ============================================================================
# JOB SKILL REQUIREMENT ADMIN
# ============================================================================

@admin.register(JobSkillRequirement)
class JobSkillRequirementAdmin(admin.ModelAdmin):
    """Admin interface for JobSkillRequirement many-to-many relationship."""
    
    list_display = ['get_job_title', 'skill', 'get_skill_category']
    list_filter = ['skill__category']
    search_fields = ['job__title', 'skill__skill_name']
    ordering = ['job__title']
    
    def get_job_title(self, obj):
        """Display job title for easier browsing."""
        return obj.job.title
    get_job_title.short_description = 'Job'
    
    def get_skill_category(self, obj):
        """Display skill category for filtering."""
        return obj.skill.category
    get_skill_category.short_description = 'Category'


# ============================================================================
# BOOKMARK ADMIN (NEW!)
# ============================================================================

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    """Admin interface for Bookmark model."""
    
    list_display = ['get_job_title', 'get_company', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['job__title', 'job__company', 'notes']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Bookmarked Job', {
            'fields': ('job',)
        }),
        ('Application Progress', {
            'fields': ('status', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  
        }),
    )
    
    def get_job_title(self, obj):
        """Display job title for the bookmark."""
        return obj.job.title
    get_job_title.short_description = 'Job Title'
    
    def get_company(self, obj):
        """Display company name for the bookmark."""
        return obj.job.company
    get_company.short_description = 'Company'
    
    # Add action to mark bookmarks as applied
    actions = ['mark_as_applied', 'mark_as_interviewing']
    
    def mark_as_applied(self, request, queryset):
        """Bulk action to mark selected bookmarks as applied."""
        updated = queryset.update(status='applied')
        self.message_user(request, f'{updated} bookmark(s) marked as applied.')
    mark_as_applied.short_description = 'Mark selected as Applied'
    
    def mark_as_interviewing(self, request, queryset):
        """Bulk action to mark selected bookmarks as interviewing."""
        updated = queryset.update(status='interviewing')
        self.message_user(request, f'{updated} bookmark(s) marked as interviewing.')
    mark_as_interviewing.short_description = 'Mark selected as Interviewing'