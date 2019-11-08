from django.conf import settings
from django.utils import timezone

from rest_base.utils.registry import ModuleRegistry

__all__ = ['base_settings']


DJANGO_REST_BASE_DEFAULT = {
    # commands
    'PREDEFINED_ROOT': 'predefined',

    # admin
    'ADMIN_NULL_STRING': '-',
    'MAX_FOREIGN_OBJECT_PREVIEW': 8,

    # authentication
    'AUTHENTICATION_MODEL': None,

    # errors
    'SENTRY_HOST': None,
    'SENTRY_VERBOSE': False,

    # models
    'MAX_UNIQUE_COLLISION_CHECK': 16,
    'DB_BATCH_SIZE': 1024,
    'DEFAULT_TOKEN_DURATION': timezone.timedelta(days=1),

    'USERNAME_LENGTH_MAX': 24,
    'PASSWORD_LENGTH_MAX': 128,

    'NONCE_WINDOW_SIZE': 8,
    'NONCE_MAX': 1 << 31,

    # utils
    'IP_HEADERS': ['HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR'],
}

base_settings = ModuleRegistry('base_settings', include_module=True)
base_settings.update(DJANGO_REST_BASE_DEFAULT)

user_settings = getattr(settings, 'REST_BASE', None)
if user_settings is not None:
    base_settings.update(user_settings)
