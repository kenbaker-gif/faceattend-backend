import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Request


class LogLoginTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.auth_extra = importlib.import_module("app.routes.auth_extra")

    def _request_with_body(self, payload: dict) -> Request:
        req = MagicMock(spec=Request)
        req.json = AsyncMock(return_value=payload)
        req.headers = {}
        req.client = SimpleNamespace(host="127.0.0.1")
        return req

    async def test_dashboard_login_writes_when_webhook_logged_recently(self):
        """Dashboard must not be blocked by a recent webhook auth.login."""
        user = SimpleNamespace(id="user-1", email="admin@test.com")
        request = self._request_with_body({"source": "dashboard"})

        audit_inserts = []

        class FakeAuditQuery:
            def __init__(self):
                self.filters = []

            def select(self, *_args, **_kwargs):
                return self

            def eq(self, key, value):
                self.filters.append((key, value))
                return self

            def gte(self, *_args, **_kwargs):
                return self

            def limit(self, *_args, **_kwargs):
                return self

            def execute(self):
                return SimpleNamespace(
                    data=[{
                        "id": "existing",
                        "metadata": {"source": "supabase_webhook"},
                    }]
                )

        class FakeProfilesQuery:
            def select(self, *_args, **_kwargs):
                return self

            def eq(self, *_args, **_kwargs):
                return self

            def limit(self, *_args, **_kwargs):
                return self

            def execute(self):
                return SimpleNamespace(data=[{"institution_id": "INST_A"}])

        class FakeAdmin:
            def table(self, name):
                if name == "audit_logs":
                    return FakeAuditQuery()
                if name == "profiles":
                    return FakeProfilesQuery()
                raise AssertionError(name)

        with patch.object(self.auth_extra, "supabase_admin", FakeAdmin()):
            with patch.object(self.auth_extra, "log_event", AsyncMock()) as log_event:
                result = await self.auth_extra.log_login(
                    request=request,
                    current_user=user,
                )

        self.assertEqual(result["message"], "login logged")
        log_event.assert_awaited_once()
        call_kwargs = log_event.await_args.kwargs
        self.assertEqual(call_kwargs["metadata"]["source"], "dashboard")

    async def test_dashboard_login_skips_duplicate_dashboard_source(self):
        user = SimpleNamespace(id="user-1", email="admin@test.com")
        request = self._request_with_body({"source": "dashboard"})

        class FakeAuditQuery:
            def select(self, *_args, **_kwargs):
                return self

            def eq(self, *_args, **_kwargs):
                return self

            def gte(self, *_args, **_kwargs):
                return self

            def limit(self, *_args, **_kwargs):
                return self

            def execute(self):
                return SimpleNamespace(
                    data=[{"id": "x", "metadata": {"source": "dashboard"}}]
                )

        class FakeProfilesQuery:
            def select(self, *_args, **_kwargs):
                return self

            def eq(self, *_args, **_kwargs):
                return self

            def limit(self, *_args, **_kwargs):
                return self

            def execute(self):
                return SimpleNamespace(data=[{"institution_id": "INST_A"}])

        class FakeAdmin:
            def table(self, name):
                if name == "audit_logs":
                    return FakeAuditQuery()
                if name == "profiles":
                    return FakeProfilesQuery()
                raise AssertionError(name)

        with patch.object(self.auth_extra, "supabase_admin", FakeAdmin()):
            with patch.object(self.auth_extra, "log_event", AsyncMock()) as log_event:
                result = await self.auth_extra.log_login(
                    request=request,
                    current_user=user,
                )

        self.assertEqual(result["message"], "already logged")
        log_event.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
