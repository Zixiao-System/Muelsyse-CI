import os

settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'muelsyse.settings.development')

if settings_module == 'muelsyse.settings.development':
    from .development import *
elif settings_module == 'muelsyse.settings.production':
    from .production import *
elif settings_module == 'muelsyse.settings.self_hosted':
    from .self_hosted import *
else:
    from .base import *
