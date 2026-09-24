"""Focused checks for the consumer page and preserved URL surface."""

from datetime import date

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from api.models import JobPosting, JobSkillRequirement, Skill


class ConsumerInterfaceTests(TestCase):
    def test_app_returns_200_and_database_counts(self):
        skill = Skill.objects.create(skill_name='Python', category='LANGUAGE')
        job = JobPosting.objects.create(
            job_link='https://example.com/jobs/1', title='Engineer', company='Example',
            location='Helsinki', country='Finland', posted_date=date(2024, 1, 12),
            experience_level='Entry level', work_type='Hybrid', search_country='Finland',
        )
        JobSkillRequirement.objects.create(job=job, skill=skill)

        response = self.client.get('/app/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'app.html')
        self.assertEqual(response.context['counts'], {
            'jobs': 1, 'skills': 1, 'relationships': 1,
        })
        self.assertIn('csrftoken', response.cookies)

    def test_local_frontend_assets_are_discoverable(self):
        response = self.client.get('/app/')
        self.assertContains(response, '/static/api/app.css')
        self.assertContains(response, '/static/api/app.js')
        self.assertContains(response, '/static/api/favicon.svg')
        self.assertIsNotNone(finders.find('api/app.css'))
        self.assertIsNotNone(finders.find('api/app.js'))
        self.assertIsNotNone(finders.find('api/favicon.svg'))

    def test_existing_routes_still_resolve(self):
        self.assertEqual(reverse('index'), '/')
        self.assertContains(self.client.get('/'), 'href="/app/"')
        self.assertEqual(reverse('swagger'), '/swagger/')
        self.assertEqual(reverse('redoc'), '/redoc/')
        self.assertEqual(reverse('admin:index'), '/admin/')
        self.assertEqual(reverse('skills-most-demanded'), '/api/skills/most-demanded/')
        self.assertEqual(reverse('skills-for-role'), '/api/skills/for-role/')
        self.assertEqual(reverse('jobs-by-skills'), '/api/jobs/by-skills/')
        self.assertEqual(reverse('skill-combinations'), '/api/skills/combinations/')
        self.assertEqual(reverse('bookmark-list-create'), '/api/bookmarks/')
        self.assertEqual(reverse('bookmark-detail', args=[1]), '/api/bookmarks/1/')
        self.assertEqual(self.client.get('/api/skills/most-demanded/').status_code, 200)
