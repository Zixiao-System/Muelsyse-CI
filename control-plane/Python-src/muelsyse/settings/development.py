from .base import *

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Add debug toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

INTERNAL_IPS = ['127.0.0.1']

# Use console email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable tenant middleware in development if running locally without DB
# MIDDLEWARE = [m for m in MIDDLEWARE if 'Tenant' not in m]
