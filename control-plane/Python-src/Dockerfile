FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

# Copy application code
COPY . .

# Set production settings for collectstatic
ENV DJANGO_SETTINGS_MODULE=muelsyse.settings.self_hosted
ENV SECRET_KEY=build-time-key-not-for-production

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN useradd -m -u 1000 muelsyse && \
    chown -R muelsyse:muelsyse /app

USER muelsyse

EXPOSE 8000

CMD ["gunicorn", "muelsyse.wsgi:application", "-b", "0.0.0.0:8000"]
