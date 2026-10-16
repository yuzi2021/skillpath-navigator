#!/usr/bin/env sh
set -eu

python manage.py migrate --noinput
python manage.py load_data

exec gunicorn skillpath.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
