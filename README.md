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
  -> SQLite locally, or PostgreSQL when configured
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
| `/app/` | Interactive demonstration of the REST API using the historical snapshot |
| `/api/` | Existing REST API used by the consumer interface |
| `/swagger/` | Interactive API documentation |
| `/admin/` | Django administration |

The original project-information page remains at `/`, and ReDoc remains at
`/redoc/`. The `/app/` page is an interactive demonstration of the existing
REST API, not a live job-search service. It uses a Django template, local CSS,
and vanilla JavaScript `fetch()` calls to the API. Its three overview counts are
read from the database. It adds no frontend build system or new analytical API.
Bookmarks are shared because the original API has no user ownership; avoid
storing private notes.

## Ubuntu setup without Docker

Use Python 3.12 (the local test version). Ubuntu may need `python3-venv`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py load_data
python manage.py runserver
```

No `.env`, PostgreSQL server, or Docker installation is required. With no
database environment variables, Django uses the ignored local `db.sqlite3`.
Open <http://127.0.0.1:8000/app/> for the interactive API demonstration; `/`
remains the project-information page.

`load_data` inserts the snapshot; running it again skips existing keys and
reports them. Use `--data-dir PATH` to test another three-file snapshot.
`--clear` deletes imported jobs, skills, links, **and bookmarks** before
reloading, inside one transaction. Validation occurs before this deletion.
Back up any data you want to retain before using it.

### Optional local PostgreSQL

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

`DATABASE_URL` takes precedence when present. Otherwise, setting
`DB_ENGINE=postgresql` uses the individual `DB_*` variables. With neither set,
SQLite remains the default. `SQLITE_PATH` can override the local database path.

## Infrastructure audit

The deployed core is synchronous Django backed by PostgreSQL. Search, role and
skill analysis, bookmarks, API operations, Swagger/ReDoc, and the consumer UI
require Django and the database only. If a non-critical documentation asset is
unavailable, the data workflows continue to operate.

This repository does **not** currently contain Celery tasks, a Celery app,
Channels consumers, WebSocket routes, or Redis-backed functionality, and no
commit in its Git history contains those components. Nothing was removed for
deployment, but it would be inaccurate to claim that Redis/Celery/Channels run
locally or publicly. If those features exist in another SkillPath source tree,
they must be merged before a worker/Redis/Channels architecture can be deployed
honestly.

## Docker Compose

Docker Compose runs the Django development server with PostgreSQL 16. Create a
local `.env` first; the web container overrides
`DB_ENGINE` and `DB_HOST` to use the `db` service.
The database has a persistent named volume, and the web service waits for the
PostgreSQL health check before running migrations, idempotently loading the
checked-in demonstration snapshot, and starting.

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
| `DB_CONN_MAX_AGE` | Persistent database connection lifetime in seconds | `60` for URL configuration |
| `DB_DISABLE_SERVER_SIDE_CURSORS` | Disable cursors incompatible with transaction pooling | auto-enabled for `-pooler` hosts |
| `DB_ENGINE` | `postgresql` or `sqlite` | `sqlite` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL database credentials | `skillpath`, `skillpath`, empty password |
| `DB_HOST`, `DB_PORT` | PostgreSQL address | `localhost`, `5432` |
| `SQLITE_PATH` | SQLite database file | `db.sqlite3` in project root |
| `DJANGO_SECRET_KEY` | Django signing secret | Development-only fallback |
| `DJANGO_DEBUG` | Debug mode | `true` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names | `localhost,127.0.0.1` |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS | `false` locally, `true` when debug is off |
| `DJANGO_SECURE_HSTS_SECONDS` | HSTS duration in seconds | `0` locally, `3600` when debug is off |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_SECURE_HSTS_PRELOAD` | Production HSTS directives | off locally, on when debug is off |

The settings reject an unset secret key when debug mode is disabled. The
Compose setup and `runserver` are development tooling. Production deployments
use Gunicorn and WhiteNoise, with collected static assets in `staticfiles/`.

## Public demo deployment: Render + Neon

[`render.yaml`](render.yaml) defines one free Render web service and requires an
external `DATABASE_URL`. It does not create Render PostgreSQL. The public demo
must use persistent Neon PostgreSQL; production startup fails fast on Render if
`DATABASE_URL` is absent, preventing an accidental fallback to ephemeral
SQLite.

Create a Neon project near the Render service, select the pooled connection URL,
and verify that its hostname contains `-pooler` and its query string contains
`sslmode=require`. Store that complete URL only in Render's secret environment
settings. Never commit it. Pooled Neon hosts automatically disable Django's
server-side cursors for transaction-pooler compatibility.

To deploy after pushing the repository:

1. Sign in to Render and connect GitHub, granting Render access only to this
   private repository if desired.
2. In **Blueprints**, choose **New Blueprint Instance**, select this repository,
   and apply its `render.yaml` from the default branch.
3. Supply the secret `DATABASE_URL` when prompted.
4. Wait for `/healthz/` to pass, then open the public
   `https://<service>.onrender.com/app/` URL and smoke-test skill search and job
   matching.

`build.sh` installs dependencies and collects static files without changing the
database. Because Render's free web tier does not provide a separate pre-deploy
command, `start.sh` applies idempotent migrations and idempotently loads the
checked-in January 2024 snapshot before starting Gunicorn. Existing rows and
bookmarks remain in Neon across restarts and redeploys; the application does not
depend on local filesystem persistence.

`/healthz/` checks the critical database connection with `SELECT 1`. Django
enables connection health checks and bounded persistent connections so stale
connections can be replaced after Neon resumes. The configuration remains
portable to any PostgreSQL provider through `DATABASE_URL`.

Render free web services may sleep when inactive, so the first request can have
a cold-start delay. Do not use artificial keep-alive traffic to bypass the
provider's sleep policy.

Run the automated suite against the Docker PostgreSQL service before release:

```bash
docker compose run --rm web python manage.py test -v 2
```

This exercises migrations, the deterministic import, API operations, model
relationships and constraints, the consumer interface, and the database-backed
health endpoint against PostgreSQL. Authentication is not part of the public
API design: endpoints use `AllowAny`, and bookmarks are intentionally shared.
Do not claim authenticated or user-owned operations unless that design changes.

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
opens the connection and asserts that Django reports the PostgreSQL backend,
migrates the database, validates the checked-in CSVs without loading them, and
runs the full test suite against PostgreSQL. If PostgreSQL is unavailable, the
connection assertion fails instead of falling back to SQLite. Ordinary local
checks use SQLite without extra configuration.

## Scope and limitations

The coursework API and bookmark behavior are retained. The new pipeline and
infrastructure demonstrate local data engineering practices; the snapshot is
historical and does not update automatically. API permissions still allow
anonymous access, and bookmarks are shared rather than user-owned. The Render
configuration serves static assets, relies on Render for managed TLS, and
requires persistent PostgreSQL through `DATABASE_URL`. Review the shared-write
behavior before promoting the demo beyond portfolio use. With default local
development settings, `python manage.py check --deploy` warns because debug mode and the
development-only secret are intentional local defaults; the Blueprint
overrides both in production.
