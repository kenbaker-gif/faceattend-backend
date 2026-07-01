"""Compatibility shim for the older admin_students import path."""

import sys

from app.routes.admin import students as _students

sys.modules[__name__] = _students