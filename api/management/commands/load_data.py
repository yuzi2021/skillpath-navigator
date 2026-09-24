"""Load the three checked-in CSV files as one validated dataset snapshot."""

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from api.etl import FILES, RowCounts, extract, load, transform, validate


class Command(BaseCommand):
    help = 'Validate and load SkillPath jobs, skills, and job-skill links'

    def add_arguments(self, parser):
        parser.add_argument('--data-dir', type=Path, default=settings.BASE_DIR / 'data',
                            help='Directory containing the three CSV files')
        parser.add_argument('--clear', action='store_true',
                            help='Replace imported data (also removes bookmarks)')
        parser.add_argument('--validate-only', action='store_true',
                            help='Check CSV quality without writing to the database')

    def handle(self, *args, **options):
        counts = {table: RowCounts() for table in FILES}
        try:
            extracted = extract(options['data_dir'])
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            raise CommandError(f'Extract failed: {exc}') from exc

        valid, issues = validate(extracted, counts)
        if issues:
            self._summary(counts)
            for issue in issues[:10]:
                self.stderr.write(issue)
            raise CommandError(f'Validation rejected {len(issues)} row(s); database unchanged.')

        if options['validate_only']:
            self._summary(counts)
            self.stdout.write(self.style.SUCCESS('Validation passed; database unchanged.'))
            return

        records = transform(valid)
        load(records, counts, clear=options['clear'])
        self._summary(counts)
        self.stdout.write(self.style.SUCCESS('Data loaded successfully.'))

    def _summary(self, counts):
        for table, filename in FILES.items():
            item = counts[table]
            reasons = ', '.join(f'{reason}={amount}' for reason, amount in sorted(item.reasons.items()))
            self.stdout.write(
                f'{filename}: processed={item.processed} loaded={item.loaded} '
                f'skipped={item.skipped} rejected={item.rejected}'
                + (f' reasons: {reasons}' if reasons else '')
            )
