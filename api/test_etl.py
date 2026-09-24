"""Integration tests for the CSV import command and its quality gates."""

import csv
import io
import tempfile
from copy import deepcopy
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from api.etl import FILES, HEADERS
from api.models import JobPosting, JobSkillRequirement, Skill


class LoadDataTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = Path(self.temp_dir.name)
        self.job_url = 'https://example.com/jobs/1'
        self.rows = {
            'skills': [{'skill_name': 'Python', 'category': 'LANGUAGE'}],
            'jobs': [{
                'job_link': self.job_url, 'title': 'Data Engineer',
                'company': 'Example', 'location': 'Helsinki', 'city': 'Helsinki',
                'state_province': '', 'country': 'Finland',
                'posted_date': '2024-01-12', 'experience_level': 'Entry level',
                'work_type': 'Hybrid', 'search_country': 'Finland',
            }],
            'links': [{'job_link': self.job_url, 'skill_name': 'Python'}],
        }

    def write_csvs(self):
        for table, filename in FILES.items():
            with (self.data_dir / filename).open('w', encoding='utf-8', newline='') as target:
                writer = csv.DictWriter(target, fieldnames=HEADERS[table])
                writer.writeheader()
                writer.writerows(self.rows[table])

    def run_import(self, **options):
        output = io.StringIO()
        errors = io.StringIO()
        call_command('load_data', data_dir=self.data_dir, stdout=output,
                     stderr=errors, **options)
        return output.getvalue()

    def test_load_and_repeat_skip_existing_rows(self):
        self.write_csvs()
        first = self.run_import()
        second = self.run_import()
        self.assertIn('processed=1 loaded=1 skipped=0 rejected=0', first)
        self.assertIn('processed=1 loaded=0 skipped=1 rejected=0', second)
        self.assertEqual((JobPosting.objects.count(), Skill.objects.count(),
                          JobSkillRequirement.objects.count()), (1, 1, 1))

    def test_validate_only_does_not_write(self):
        self.write_csvs()
        self.assertIn('Validation passed', self.run_import(validate_only=True))
        self.assertEqual(JobPosting.objects.count(), 0)

    def test_invalid_date_rejects_without_fallback(self):
        self.rows['jobs'][0]['posted_date'] = 'not-a-date'
        self.write_csvs()
        with self.assertRaisesRegex(CommandError, 'database unchanged'):
            self.run_import()
        self.assertEqual(JobPosting.objects.count(), 0)

    def test_future_date_rejected_as_out_of_range(self):
        self.rows['jobs'][0]['posted_date'] = '2999-01-01'
        self.write_csvs()
        with self.assertRaisesRegex(CommandError, 'database unchanged'):
            self.run_import()
        self.assertEqual(JobPosting.objects.count(), 0)

    def test_missing_required_field_rejects_dataset(self):
        self.rows['jobs'][0]['title'] = '  '
        self.write_csvs()
        with self.assertRaisesRegex(CommandError, 'database unchanged'):
            self.run_import()
        self.assertEqual(JobPosting.objects.count(), 0)

    def test_invalid_job_url_rejects_dataset(self):
        self.rows['jobs'][0]['job_link'] = 'not-a-url'
        self.rows['links'][0]['job_link'] = 'not-a-url'
        self.write_csvs()
        with self.assertRaisesRegex(CommandError, 'database unchanged'):
            self.run_import()
        self.assertEqual(JobPosting.objects.count(), 0)

    def test_duplicate_source_row_is_reported_and_skipped(self):
        self.rows['skills'].append(deepcopy(self.rows['skills'][0]))
        self.write_csvs()
        output = self.run_import()
        self.assertIn('duplicate_in_source=1', output)
        self.assertEqual(Skill.objects.count(), 1)

    def test_conflicting_duplicate_rejects_dataset(self):
        self.rows['skills'].append({'skill_name': 'Python', 'category': 'TOOL'})
        self.write_csvs()
        with self.assertRaisesRegex(CommandError, 'database unchanged'):
            self.run_import()
        self.assertEqual(Skill.objects.count(), 0)

    def test_unknown_skill_reference_rejected_and_clear_keeps_old_data(self):
        self.write_csvs()
        self.run_import()
        self.rows['links'][0]['skill_name'] = 'Missing'
        self.write_csvs()
        with self.assertRaisesRegex(CommandError, 'database unchanged'):
            self.run_import(clear=True)
        self.assertEqual(JobSkillRequirement.objects.count(), 1)

    def test_missing_input_file_is_an_error(self):
        self.write_csvs()
        (self.data_dir / FILES['links']).unlink()
        with self.assertRaisesRegex(CommandError, 'Missing input file'):
            self.run_import()

    def test_wrong_csv_header_is_an_error(self):
        self.write_csvs()
        (self.data_dir / FILES['skills']).write_text('wrong,header\nPython,LANGUAGE\n')
        with self.assertRaisesRegex(CommandError, 'expected columns'):
            self.run_import()
