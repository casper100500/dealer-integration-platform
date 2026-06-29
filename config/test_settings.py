from .settings import *  # noqa: F401,F403

CELERY_TASK_ALWAYS_EAGER = True
OPENSEARCH_AUDIT_LOGS_ENABLED = False
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
