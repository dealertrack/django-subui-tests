from __future__ import print_function, unicode_literals

import django
from django.conf import settings


settings.configure(
    LOGGING_CONFIG={},
)
django.setup()
