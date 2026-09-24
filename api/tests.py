"""
Unit tests for SkillPath Navigator API

Tests all 6 API endpoints, error handling, CRUD operations, model relationships,
and edge cases. Uses Factory Boy for test data generation.

COVERAGE:
- 29 comprehensive tests
- Achieves 82% overall code coverage (91% on endpoints, 100% on models/serializers)
- Tests edge cases and validation logic
- Covers serializer methods
- Tests model __str__ methods
- Tests model relationships

Test Coverage Breakdown:
- Endpoint functionality: 10 tests (basic endpoint responses)
- Error handling: 9 tests (missing params, invalid values, 404s)
- CRUD operations: 5 tests (bookmark create, read, update, delete)
- Model tests: 5 tests (__str__ methods, relationships)

Total: 29 tests across 2 test classes

RUNNING TESTS WITH COVERAGE:
============================
1. Install coverage tool:
   pip install coverage

2. Run tests with coverage tracking:
   coverage run --source='api' manage.py test

3. View coverage report:
   coverage report

References:
- CM3035 Topic 4: Unit Testing
- Factory Boy documentation
- Django TestCase documentation
- Coverage.py documentation
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from api.models import Skill, JobPosting, JobSkillRequirement, Bookmark
from datetime import date
import factory
from factory.django import DjangoModelFactory

# ============================================================================
# FACTORY BOY FACTORIES - Test Data Generation
# ============================================================================

class SkillFactory(DjangoModelFactory):
    """Factory for creating Skill test instances."""
    
    class Meta:
        model = Skill
        django_get_or_create = ('skill_name',)

    skill_name = factory.Sequence(lambda n: f'Skill{n}')
    category = factory.Iterator(['LANGUAGE', 'FRAMEWORK', 'DATABASE', 'TOOLS', 'CLOUD_DEVOPS' ])

class JobPostingFactory(DjangoModelFactory):
    """Factory for creating JobPosting test instances."""

    class Meta:
        model = JobPosting
        django_get_or_create = ('job_link',)
    
    job_link = factory.Sequence(lambda n: f'https://linkedin.com/jobs/test-{n}')
    title = factory.Iterator([
        'Backend Developer',
        'Frontend Developer',
        'Data Analyst',
        'Full Stack Engineer',
        'Junior Coder'
    ])
    company = factory.Iterator(['TechCorp', 'Webco', 'DataInc', 'StartupXYZ'])
    location = 'Remote'
    city = ''
    state_province = ''
    country = 'United States'
    posted_date = factory.LazyFunction(date.today)
    experience_level = 'Entry level'
    work_type = factory.Iterator(['Remote', 'Hybrid', 'Onsite'])
    search_country = 'United States'

class BookmarkFactory(DjangoModelFactory):
    """Factory for creating Bookmark test instances."""
    
    class Meta:
        model = Bookmark
    
    job = factory.SubFactory(JobPostingFactory)
    notes = factory.Faker('sentence')
    status = factory.Iterator(['interested', 'applied', 'interviewing'])


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================

class SkillPathAPITestCase(TestCase):
    """Test suite for SkillPath Navigator API endpoints."""

    def setUp(self):
        """Create test data using Factory Boy before each test."""
        self.client = APIClient()

        # Create skills using factories
        self.python = SkillFactory(skill_name='Python', category='LANGUAGE')
        self.sql = SkillFactory(skill_name='SQL', category='DATABASE')
        self.django = SkillFactory(skill_name='Django', category='FRAMEWORK')
        self.git = SkillFactory(skill_name='Git', category='TOOLS')
        self.aws = SkillFactory(skill_name='AWS', category='CLOUD_DEVOPS')

        # Create jobs using factories
        self.job1 = JobPostingFactory(
            job_link='http://linkedin.com/jobs/1',
            title='Backend Developer',
            company='TechCorp'
        )

        self.job2 = JobPostingFactory(
            job_link='http://linkedin.com/jobs/2',
            title='Data Analyst',
            company='DataCorp'
        )

        self.job3 = JobPostingFactory(
            job_link='http://linkedin.com/jobs/3',
            title='Junior Coder',
            company='StartupXYZ'
        )

        # Create job-skill relationships
        JobSkillRequirement.objects.create(job=self.job1, skill=self.python)
        JobSkillRequirement.objects.create(job=self.job1, skill=self.sql)
        JobSkillRequirement.objects.create(job=self.job1, skill=self.django)
        
        JobSkillRequirement.objects.create(job=self.job2, skill=self.python)
        JobSkillRequirement.objects.create(job=self.job2, skill=self.sql)
        
        JobSkillRequirement.objects.create(job=self.job3, skill=self.python)           

    # ENDPOINT 1

    def test_skills_most_demanded_success(self):
        """Test GET /api/skills/most-demanded/ returns top skills."""
        response = self.client.get('/api/skills/most-demanded/', follow=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)

        # Verify response structure
        first_skill = response.data[0]
        self.assertIn('skill_name', first_skill)
        self.assertIn('category', first_skill)
        self.assertIn('job_count', first_skill)

        # Python should be most demanded (appears in all 3 jobs)
        self.assertEqual(first_skill['skill_name'], 'Python')
        self.assertEqual(first_skill['job_count'], 3)

    # ENDPOINT 2

    def test_skills_for_role_success(self):
        """Test GET /api/skills/for-role/?role=backend"""
        response = self.client.get('/api/skills/for-role/?role=backend')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('role', response.data)
    
    def test_skills_for_role_missing_parameter(self):
        """Test missing role parameter returns 400."""
        response = self.client.get('/api/skills/for-role/')
        self.assertEqual(response.status_code, status. HTTP_400_BAD_REQUEST)
    
    def test_skills_for_role_invalid_role(self):
          """Test invalid role returns 400."""
          response = self.client.get('/api/skills/for-role/?role=invalid') 
          self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_skills_for_role_multiple_roles(self):
        """Test different roles work."""
        response = self.client.get('/api/skills/for-role/?role=data')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response2 = self.client.get('/api/skills/for-role/?role=software')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)    

    # ENDPOINT 3

    def test_jobs_by_skills_success(self):
        """Test GET /api/jobs/by-skills/?skills=Python,SQL"""
        response = self.client.get('/api/jobs/by-skills/?skills=Python,SQL')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('jobs', response.data)
    
    def test_jobs_by_skills_missing_parameter(self):
        """Test missing skills returns 400."""
        response = self.client.get('/api/jobs/by-skills/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_jobs_by_skills_case_insensitive(self):
        """Test case-insensitive matching."""
        response = self.client.get('/api/jobs/by-skills/?skills=python')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_jobs_by_skills_single_skill(self):
        """Test single skill matching."""
        response = self.client.get('/api/jobs/by-skills/?skills=Python')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_jobs_by_skills_empty_string(self):
        """Test empty skills string returns 400."""
        response = self.client.get('/api/jobs/by-skills/?skills=')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    # ENDPOINT 4
    def test_skill_combinations_success(self):
        """Test GET /api/skills/combinations/?skill=Python"""
        response = self.client.get('/api/skills/combinations/?skill=Python')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('base_skill', response.data)
    
    def test_skill_combinations_missing_parameter(self):
        """Test missing skill parameter."""
        response = self.client.get('/api/skills/combinations/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_skill_combinations_not_found(self):
        """Test invalid skill returns 404."""
        response = self.client.get('/api/skills/combinations/?skill=InvalidSkill')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_skill_combinations_case_insensitive(self):
        """Test case-insensitive skill lookup."""
        response = self.client.get('/api/skills/combinations/?skill=python')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    # ENDPOINT 5
    def test_bookmark_list_get(self):
        """Test GET /api/bookmarks/"""
        BookmarkFactory(job=self.job1)
        response = self.client.get('/api/bookmarks/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_bookmark_create_post_success(self):
        """Test POST /api/bookmarks/"""
        data = {'job_link': self.job2.job_link, 'notes': 'Test', 'status': 'interested'}
        response = self.client.post('/api/bookmarks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_bookmark_create_missing_job_link(self):
        """Test POST without job_link returns 400."""
        data = {'notes': 'Test'}
        response = self.client.post('/api/bookmarks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_bookmark_create_invalid_job_link(self):
        """Test POST with invalid job_link returns 400."""
        data = {'job_link': 'https://invalid.com/999', 'notes': 'Test'}
        response = self.client.post('/api/bookmarks/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_bookmark_list_filter_by_status(self):
        """Test status filtering."""
        BookmarkFactory(job=self.job1, status='applied')
        response = self.client.get('/api/bookmarks/?status=applied')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    # ENDPOINT 6
    def test_bookmark_retrieve_get(self):
        """Test GET /api/bookmarks/{id}/"""
        bookmark = BookmarkFactory(job=self.job1, notes='Test note')
        response = self.client.get(f'/api/bookmarks/{bookmark.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'Test note')
    
    def test_bookmark_update_patch(self):
        """Test PATCH /api/bookmarks/{id}/"""
        bookmark = BookmarkFactory(job=self.job1, status='interested')
        response = self.client.patch(f'/api/bookmarks/{bookmark.id}/', {'status': 'applied'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.status, 'applied')
    
    def test_bookmark_update_notes_only(self):
        """Test partial PATCH."""
        bookmark = BookmarkFactory(job=self.job1, notes='Old', status='interested')
        response = self.client.patch(f'/api/bookmarks/{bookmark.id}/', {'notes': 'New'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.status, 'interested')
    
    def test_bookmark_delete(self):
        """Test DELETE /api/bookmarks/{id}/"""
        bookmark = BookmarkFactory(job=self.job1)
        response = self.client.delete(f'/api/bookmarks/{bookmark.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Bookmark.objects.count(), 0)
    
    def test_bookmark_not_found(self):
        """Test 404 for non-existent bookmark."""
        response = self.client.get('/api/bookmarks/999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ============================================================================
# MODEL TESTS
# ============================================================================

class ModelTestCase(TestCase):
    """Test models and relationships."""
    
    def test_job_posting_str(self):
        """Test JobPosting __str__ method."""
        job = JobPostingFactory(title='Test Job', company='TestCo')
        self.assertEqual(str(job), 'Test Job at TestCo')
    
    def test_skill_str(self):
        """Test Skill __str__ method."""
        skill = SkillFactory(skill_name='Python', category='LANGUAGE')
        self.assertEqual(str(skill), 'Python (LANGUAGE)')
    
    def test_bookmark_str(self):
        """Test Bookmark __str__ method."""
        job = JobPostingFactory(title='Dev', company='Co')
        bookmark = BookmarkFactory(job=job, status='applied')
        self.assertEqual(str(bookmark), 'Bookmark: Dev at Co (applied)')
    
    def test_job_skill_requirement_str(self):
        """Test JobSkillRequirement __str__ method."""
        job = JobPostingFactory(title='Engineer')
        skill = SkillFactory(skill_name='Python')
        req = JobSkillRequirement.objects.create(job=job, skill=skill)
        self.assertEqual(str(req), 'Engineer requires Python')
    
    def test_many_to_many_relationship(self):
        """Test job-skill relationship."""
        job = JobPostingFactory()
        skill = SkillFactory(skill_name='Python')
        JobSkillRequirement.objects.create(job=job, skill=skill)
        self.assertEqual(job.skills.count(), 1)
        self.assertEqual(skill.jobs.count(), 1)