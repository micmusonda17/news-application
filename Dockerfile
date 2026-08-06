# Dockerfile for the News Application
#
# This builds a small image that runs the Django news app with Gunicorn.
# Only the source code and the packages in requirements.txt go into the
# image. The secret key and the database settings are read from
# environment variables at run time, so no secrets are baked in.
#
# The project talks to MariaDB through PyMySQL, which is pure Python, so
# no compiler or MySQL C libraries are needed here.

FROM python:3.12-slim

# PYTHONDONTWRITEBYTECODE stops .pyc files being written inside the image.
# PYTHONUNBUFFERED makes print() and log output appear straight away.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install the requirements first, in their own layer. Docker can reuse
# this layer whenever only the source code has changed.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn==23.0.0

# Now copy the rest of the project.
COPY . .

# Run as a normal user rather than root, which is safer.
RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

# Gunicorn listens on this port inside the container.
EXPOSE 8000

# Defaults so that the container starts up on its own with SQLite.
# To use MariaDB instead, set USE_SQLITE=False and the DB_* variables.
# DJANGO_ALLOWED_HOSTS is "*" so the container also works on Docker
# Playground or another machine, where the hostname is not localhost.
ENV DJANGO_SETTINGS_MODULE=news_project.settings \
    USE_SQLITE=True \
    DJANGO_ALLOWED_HOSTS=*

# Apply migrations, collect the static files, then start Gunicorn.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn news_project.wsgi:application --bind 0.0.0.0:8000"]
