"""Compatibility shim for the older auth_extra import path."""

import sys

from app.routes import auth as _auth

sys.modules[__name__] = _auth