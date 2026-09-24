"""Small, explicit CSV -> validation -> model -> database pipeline.

The three CSVs are a single snapshot: links must refer to jobs and skills in
that snapshot. Validation finishes before any database writes begin.
"""

import csv
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction

from .models import JobPosting, JobSkillRequirement, Skill


FILES = {
    'skills': 'skill_categories_filtered.csv',
    'jobs': 'jobs_clean_filtered.csv',
    'links': 'skills_clean_filtered.csv',
}
HEADERS = {
    'skills': ('skill_name', 'category'),
    'jobs': (
        'job_link', 'title', 'company', 'location', 'city', 'state_province',
        'country', 'posted_date', 'experience_level', 'work_type', 'search_country',
    ),
    'links': ('job_link', 'skill_name'),
}
OPTIONAL = {'jobs': {'city', 'state_province'}}
LIMITS = {
    'skills': {'skill_name': 200, 'category': 50},
    'jobs': {
        'job_link': 500, 'title': 500, 'company': 200, 'location': 200,
        'city': 100, 'state_province': 100, 'country': 100,
        'experience_level': 50, 'work_type': 50, 'search_country': 100,
    },
    'links': {'job_link': 500, 'skill_name': 200},
}
VALID_CATEGORIES = {
    'LANGUAGE', 'FRAMEWORK', 'DATABASE', 'TOOL', 'TOOLS',
    'CLOUD_DEVOPS', 'SOFT_SKILL', 'OTHER',
}
VALID_WORK_TYPES = {'Onsite', 'Remote', 'Hybrid', 'Unknown'}
EARLIEST_POSTED_DATE = date(2000, 1, 1)
url_validator = URLValidator(schemes=['http', 'https'])


@dataclass
class RowCounts:
    processed: int = 0
    loaded: int = 0
    skipped: int = 0
    rejected: int = 0
    reasons: Counter = field(default_factory=Counter)

    def skip(self, reason):
        self.skipped += 1
        self.reasons[reason] += 1

    def reject(self, reason):
        self.rejected += 1
        self.reasons[reason] += 1


def extract(data_dir: Path):
    """Read CSV rows with their line numbers; reject missing or wrong headers."""
    extracted = {}
    for table, filename in FILES.items():
        path = data_dir / filename
        if not path.is_file():
            raise ValueError(f'Missing input file: {path}')
        with path.open(newline='', encoding='utf-8-sig') as source:
            reader = csv.DictReader(source, strict=True)
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)) or set(headers) != set(HEADERS[table]):
                raise ValueError(f'{filename}: expected columns {HEADERS[table]}, got {headers}')
            rows = list(enumerate(reader, start=2))
            if not rows:
                raise ValueError(f'{filename}: no data rows')
            extracted[table] = rows
    return extracted


def _row_error(table, row):
    """Return a stable reason category for a malformed row, or None."""
    if None in row or any(value is None for value in row.values()):
        return 'column_count'
    required = set(HEADERS[table]) - OPTIONAL.get(table, set())
    if any(not row[column] for column in required):
        return 'missing_required'
    if any(len(value) > maximum for column, maximum in LIMITS[table].items()
           if (value := row[column])):
        return 'field_too_long'

    if table == 'jobs':
        try:
            url_validator(row['job_link'])
        except ValidationError:
            return 'invalid_job_url'
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['posted_date']):
            return 'invalid_posted_date'
        try:
            posted_date = date.fromisoformat(row['posted_date'])
        except ValueError:
            return 'invalid_posted_date'
        if not EARLIEST_POSTED_DATE <= posted_date <= date.today():
            return 'posted_date_out_of_range'
        if row['work_type'] not in VALID_WORK_TYPES:
            return 'invalid_work_type'
    elif table == 'skills' and row['category'] not in VALID_CATEGORIES:
        return 'invalid_category'
    return None


def validate(extracted, counts):
    """Validate fields, duplicate keys and cross-file references."""
    valid = {}
    issues = []
    key_fields = {
        'skills': ('skill_name',),
        'jobs': ('job_link',),
        'links': ('job_link', 'skill_name'),
    }
    for table, rows in extracted.items():
        seen = {}
        valid[table] = []
        for line, raw in rows:
            counts[table].processed += 1
            row = {key: (raw.get(key) or '').strip() for key in HEADERS[table]}
            reason = ('column_count' if None in raw or any(
                value is None for value in raw.values()) else _row_error(table, row))
            if reason:
                counts[table].reject(reason)
                issues.append(f'{FILES[table]}:{line}: {reason}')
                continue
            key = tuple(row[column] for column in key_fields[table])
            if key in seen:
                if seen[key] == row:
                    counts[table].skip('duplicate_in_source')
                else:
                    counts[table].reject('conflicting_duplicate')
                    issues.append(f'{FILES[table]}:{line}: conflicting_duplicate')
                continue
            seen[key] = row
            valid[table].append((line, row))

    job_keys = {row['job_link'] for _, row in valid['jobs']}
    skill_keys = {row['skill_name'] for _, row in valid['skills']}
    good_links = []
    for line, row in valid['links']:
        reason = None
        if row['job_link'] not in job_keys:
            reason = 'unknown_job_reference'
        elif row['skill_name'] not in skill_keys:
            reason = 'unknown_skill_reference'
        if reason:
            counts['links'].reject(reason)
            issues.append(f'{FILES["links"]}:{line}: {reason}')
        else:
            good_links.append((line, row))
    valid['links'] = good_links
    return valid, issues


def transform(valid):
    """Convert clean strings to Django model instances; no writes occur here."""
    return {
        'skills': [Skill(**row) for _, row in valid['skills']],
        'jobs': [JobPosting(**{**row, 'posted_date': date.fromisoformat(row['posted_date'])})
                 for _, row in valid['jobs']],
        'links': [JobSkillRequirement(job_id=row['job_link'], skill_id=row['skill_name'])
                  for _, row in valid['links']],
    }


def load(models, counts, clear=False):
    """Insert new records atomically; repeated imports skip existing keys."""
    with transaction.atomic():
        if clear:
            JobSkillRequirement.objects.all().delete()
            JobPosting.objects.all().delete()  # Also deletes bookmarks via CASCADE.
            Skill.objects.all().delete()

        existing = {
            'skills': set(Skill.objects.values_list('skill_name', flat=True)),
            'jobs': set(JobPosting.objects.values_list('job_link', flat=True)),
            'links': set(JobSkillRequirement.objects.values_list('job_id', 'skill_id')),
        }
        for table, model, key in (
            ('skills', Skill, lambda obj: obj.skill_name),
            ('jobs', JobPosting, lambda obj: obj.job_link),
            ('links', JobSkillRequirement, lambda obj: (obj.job_id, obj.skill_id)),
        ):
            new_rows = []
            for obj in models[table]:
                if key(obj) in existing[table]:
                    counts[table].skip('already_loaded')
                else:
                    new_rows.append(obj)
            model.objects.bulk_create(new_rows, batch_size=1000)
            counts[table].loaded = len(new_rows)
