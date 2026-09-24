# SkillPath: job-skill data and analytics API

SkillPath loads a fixed snapshot of entry-level job postings and their required
skills into a relational database, then exposes skill-demand and job-matching
analyses through a Django REST Framework API. It began as a university web
development coursework project. The later portfolio engineering work adds
PostgreSQL configuration, containers, a validated CSV pipeline, analytical SQL,
and continuous integration. The added ingestion, quality, and SQL work is
relevant to operations analytics and data engineering; it is not ABB
operational data. This repository does **not** include a live job scraper, a
currently deployed instance, or a cloud analytics platform.

## Dataset and architecture

The checked-in CSV snapshot contains **464 jobs**, **319 skills**, and **5,845
job-skill relationships**. The postings are dated 12–17 January 2024; 235 have
`country=United Kingdom`, 212 have `country=United States`, and 17 have other
country values. Job URLs point mainly to LinkedIn. The original upstream
collection and cleaning scripts are not in this repository, so its provenance
cannot be reproduced from source here. There is **no salary column**.

```text
data/*.csv
  -> api/etl.py: extract -> validate -> transform -> load
  -> PostgreSQL (or optional local SQLite)
  -> Django ORM in api/api.py -> DRF serializers -> JSON API
```

`JobPosting` and `Skill` have a many-to-many relationship through
`JobSkillRequirement`. `Bookmark` refers to a job and stores notes and an
application status. The original six API routes remain in `api/urls.py`:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/skills/most-demanded/` | Top skill counts |
| `GET /api/skills/for-role/?role=data` | Skills for title-matched roles |
| `GET /api/jobs/by-skills/?skills=Python,SQL` | Job match scores |
| `GET /api/skills/combinations/?skill=Python` | Skill co-occurrence |
| `GET`, `POST /api/bookmarks/` | List or create bookmarks |
| `GET`, `PUT`, `PATCH`, `DELETE /api/bookmarks/{id}/` | Bookmark detail and changes |

The landing page is `/`; Swagger UI is `/swagger/`, ReDoc is `/redoc/`, and the
Django admin is `/admin/`.

## Interfaces

| Route | Use |
| --- | --- |
| `/app/` | Consumer interface for exploring skills, matching jobs, and tracking bookmarks |
| `/api/` | Existing REST API used by the consumer interface |
| `/swagger/` | Interactive API documentation |
| `/admin/` | Django administration |

The original project-information page remains at `/`, and ReDoc remains at
`/redoc/`. The `/app/` page uses a Django template, local CSS, and vanilla
JavaScript `fetch()` calls to the existing API. Its three overview counts are
read from the database. It adds no frontend build system or new analytical
API. Bookmarks are still shared because the original API has no user ownership;
avoid storing private notes.

## Ubuntu setup without Docker

Use Python 3.12 (the local test version). Ubuntu may need `python3-venv`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

### PostgreSQL (recommended development path)

Install and start a local PostgreSQL server, then create a database and role.
For example, after `sudo apt install postgresql`, run `sudo -u postgres psql`
and enter the following SQL once, replacing the dummy password:

```sql
CREATE USER skillpath WITH PASSWORD 'change-me-local-only';
CREATE DATABASE skillpath OWNER skillpath;
```

Copy `.env.example` to `.env`, set the same database credentials, and replace
`DJANGO_SECRET_KEY` with a random local value. The `.env` file is ignored by
Git. Django reads environment variables, so export the file in your shell:

```bash
cp .env.example .env
# Edit .env before sourcing it.
set -a
. ./.env
set +a
python manage.py migrate
python manage.py load_data --validate-only
python manage.py load_data
python manage.py runserver
```

Open <http://127.0.0.1:8000/app/> for the consumer interface; `/` remains the
project-information page. `load_data` inserts the snapshot; running it
again skips existing keys and reports them. Use `--data-dir PATH` to test
another three-file snapshot. `--clear` deletes imported jobs, skills, links,
**and bookmarks** before reloading, inside one transaction. Validation occurs
before this deletion. Back up any data you want to retain before using it.

### SQLite convenience fallback

Without `DB_ENGINE`, Django uses the existing local `db.sqlite3`. To make the
choice explicit in a shell that has loaded `.env`, set `DB_ENGINE=sqlite`.
`SQLITE_PATH` can override the file path. Run `migrate`, `load_data`, and
`runserver` as above. This path keeps the original coursework setup usable.

## Docker Compose

Docker Compose runs the Django development server and PostgreSQL 16. Create a
local `.env` first; the web container overrides `DB_HOST` to the `db` service.
The database has a persistent named volume, and the web service waits for the
PostgreSQL health check before running migrations and starting.

```bash
cp .env.example .env
# Edit .env, especially DB_PASSWORD and DJANGO_SECRET_KEY.
docker compose up --build -d
docker compose exec web python manage.py load_data --validate-only
docker compose exec web python manage.py load_data
docker compose logs web
docker compose down
```

The consumer interface is at <http://127.0.0.1:8000/app/>. `docker compose down` leaves the
database volume in place. The image uses the pinned `requirements.txt`; it
does not include the local SQLite database or `.env` file.

## Configuration

| Variable | Meaning | Default when unset |
| --- | --- | --- |
| `DATABASE_URL` | Hosted database connection URL; takes precedence over the variables below | unset |
| `DB_ENGINE` | `postgresql` or `sqlite` | `sqlite` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL database credentials | `skillpath`, `skillpath`, empty password |
| `DB_HOST`, `DB_PORT` | PostgreSQL address | `localhost`, `5432` |
| `SQLITE_PATH` | SQLite database file | `db.sqlite3` in project root |
| `DJANGO_SECRET_KEY` | Django signing secret | Development-only fallback |
| `DJANGO_DEBUG` | Debug mode | `true` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names | `localhost,127.0.0.1` |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS | `false` locally, `true` when debug is off |
| `DJANGO_SECURE_HSTS_SECONDS` | HSTS duration in seconds | `0` locally, `3600` when debug is off |

The settings reject an unset secret key when debug mode is disabled. The
Compose setup and `runserver` are development tooling. Production deployments
use Gunicorn and WhiteNoise, with collected static assets in `staticfiles/`.

## Public demo deployment (private source)

[`render.yaml`](render.yaml) defines a Render Blueprint with a public Django
web service and a PostgreSQL database. Render can read a private GitHub
repository after you authorize its GitHub App; the repository does not need to
be made public. The Blueprint generates `DJANGO_SECRET_KEY`, disables debug,
wires `DATABASE_URL` to PostgreSQL, collects static assets, runs migrations,
and idempotently loads the checked-in dataset.

To deploy after pushing the repository:

1. Sign in to Render and connect GitHub, granting Render access only to this
   private repository if desired.
2. In **Blueprints**, choose **New Blueprint Instance**, select this repository,
   and apply its `render.yaml` from the default branch.
3. Wait for the database and web-service deploy to finish, then open the public
   `https://<service>.onrender.com/app/` URL and smoke-test skill search and job
   matching.

No secret needs to be copied into the repository. `DJANGO_SECRET_KEY` and
`DATABASE_URL` are created by the Blueprint, while Render supplies its external
hostname for `ALLOWED_HOSTS`. For another host, set `DJANGO_ALLOWED_HOSTS` to a
comma-separated list of exact hostnames and provide `DATABASE_URL` plus
`DJANGO_SECRET_KEY` in that platform's secret settings.

The Blueprint deliberately selects free plans so applying it cannot silently
choose paid compute. Free web services sleep after inactivity, and free Render
PostgreSQL databases expire after 30 days. For a durable recruiter-facing URL,
change the database to a paid plan in the Render review screen before applying,
or upgrade it before the 30-day expiry. Do not use SQLite on Render for durable
bookmarks because its service filesystem is ephemeral.

## ETL and data quality

`python manage.py load_data` reads `jobs_clean_filtered.csv`,
`skill_categories_filtered.csv`, and `skills_clean_filtered.csv` from `data/`.
It checks file presence and headers; required fields and model field lengths;
job URL syntax; date format and the range 2000-01-01 through today; skill
categories and work types; duplicate keys; and references from every link to
a job and skill in the same CSV snapshot. Blank `city` and `state_province`
are allowed because the model permits them. There are no numeric measures to
range-check beyond the date. Exact duplicate source rows and existing database
keys are skipped and counted; conflicting duplicates and malformed rows reject
the entire snapshot before any database write.

The command prints processed, loaded, skipped, and rejected counts for each
file, with reason categories and sample line numbers on validation failure.
`--validate-only` checks the files without changing the database. Import is
insert-only; it does not update existing job or skill records.

## Analytics and SQL

[`analytics/queries.sql`](analytics/queries.sql) contains four runnable
analyses against the actual tables: top skills, category frequencies, jobs by
number of skills, and posting counts by country/work type. Each SQL query has
an equivalent Django ORM expression in a comment. For example:

```sql
SELECT s.skill_name, COUNT(DISTINCT r.job_id) AS job_count
FROM api_skill AS s
LEFT JOIN api_jobskillrequirement AS r ON r.skill_id = s.skill_name
GROUP BY s.skill_name
ORDER BY job_count DESC
LIMIT 20;
```

```python
Skill.objects.annotate(job_count=Count('jobs', distinct=True)).order_by('-job_count')[:20]
```

With local PostgreSQL and `.env` exported, run all examples using
`psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f analytics/queries.sql`.
The API's ORM calculations are in `api/api.py`.

## Checks, tests, and CI

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The original 29 coursework tests remain in `api/tests.py`. Focused ETL tests
are in `api/test_etl.py`. GitHub Actions installs the pinned dependencies,
starts a PostgreSQL 16 service, checks Django and migration consistency,
migrates the database, validates the checked-in CSVs without loading them,
and runs the full test suite against PostgreSQL. A local SQLite test run is
also supported by setting `DB_ENGINE=sqlite`.

## Scope and limitations

The coursework API and bookmark behavior are retained. The new pipeline and
infrastructure demonstrate local data engineering practices; the snapshot is
historical and does not update automatically. API permissions still allow
anonymous access, and bookmarks are shared rather than user-owned. The Render
configuration serves static assets and relies on Render for managed TLS. Review
the shared-write behavior before promoting the demo beyond portfolio use. With
default local development settings, `python manage.py check --deploy` still
warns because debug mode and the development-only secret are intentional local
defaults; the Blueprint overrides both in production.
