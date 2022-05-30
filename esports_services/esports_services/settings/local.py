from .common import *


MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

if DEBUG_TOOLBAR:
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1"]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} :: {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': env('LOGLEVEL'),
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': env('LOGLEVEL'),
            'class': 'logging.FileHandler',
            'filename': 'django_error.log',
            'formatter': 'verbose',
        },
    },
    'loggers':{
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'root': {
            'handlers': ['file'],
            'level': env('LOGLEVEL'),
            'propagate': True,
        }
    }
}
