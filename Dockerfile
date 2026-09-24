FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home --uid 10001 skillpath && chown -R skillpath:skillpath /app
USER skillpath

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
