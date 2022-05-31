import os.path
from .common import BASE_DIR, env

PUBLIC_HTML_DIR = '/home/c/cv28116/public_html/'
STATIC_ROOT = os.path.join(PUBLIC_HTML_DIR, 'static')
MEDIA_ROOT = os.path.join(PUBLIC_HTML_DIR, 'media')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} :: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': env('LOGLEVEL'),
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django_debug.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'root': {
            'handlers': ['file'],
            'level': env('LOGLEVEL'),
            'propagate': True,
        },
    },
}
