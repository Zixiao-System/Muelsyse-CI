"""
Celery configuration for Muelsyse-CI
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muelsyse.settings.development')

app = Celery('muelsyse')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
