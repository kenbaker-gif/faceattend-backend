"""Compatibility shim for the older admin_coordinators import path."""

import sys

from app.routes.admin import coordinators as _coordinators

# Re-point the legacy module name to the current implementation so tests and
# older imports continue to work without changing the route module internals.
sys.modules[__name__] = _coordinators
