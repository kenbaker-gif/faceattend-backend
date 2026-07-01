import unittest
from fastapi.testclient import TestClient

from app.main import app
import app.routes.admin_coordinators as admin_coordinators


class DummyUser:
    def __init__(self, user_id: str):
        self.id = user_id


class DummyResult:
    def __init__(self, data=None):
        self.data = data


class DummyTable:
    def __init__(self, table_name: str, state: dict):
        self.table_name = table_name
        self.state = state
        self.filters = {}
        self._delete = False

    def select(self, *args, **kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def single(self):
        return self

    def limit(self, _):
        return self

    def delete(self):
        self._delete = True
        return self

    def execute(self):
        if self.table_name == "profiles":
            user_id = self.filters.get("id")
            if user_id == "admin-id":
                return DummyResult({"institution_id": "inst1", "is_super_admin": True, "role": "super_admin"})
            if user_id == "lecturer-id":
                return DummyResult({"institution_id": "inst1", "role": "lecturer"})
            return DummyResult(None)

        if self.table_name == "course_units":
            return DummyResult({"institution_id": "inst1"})

        if self.table_name == "lecturer_courses":
            if self._delete:
                return DummyResult([{}])
            already_present = self.filters.get("lecturer_id") == "lecturer-id" and self.filters.get("course_unit_id") == "existing-course-unit"
            return DummyResult([{"id": "existing-assignment"}] if already_present else [])

        return DummyResult([])

    def insert(self, data):
        if self.table_name == "lecturer_courses":
            return DummyResult([{"id": "new-assignment"}])
        return DummyResult([])


class DummySupabaseAdmin:
    def __init__(self):
        self.state = {}

    def table(self, table_name):
        return DummyTable(table_name, self.state)


class LecturerCourseAssignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        admin_coordinators.supabase_admin = DummySupabaseAdmin()
        app.dependency_overrides[admin_coordinators.check_admin] = lambda: DummyUser("admin-id")
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_assign_lecturer_course_creates_assignment(self):
        response = self.client.post(
            "/admin/lecturer-courses",
            data={
                "lecturer_id": "lecturer-id",
                "course_unit_id": "course-unit-id",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["assigned"])
        self.assertEqual(payload["assignment_id"], "new-assignment")
        self.assertIn("Lecturer assigned", payload["message"])

    def test_unassign_lecturer_course_removes_assignment(self):
        response = self.client.delete(
            "/admin/lecturer-courses",
            params={
                "lecturer_id": "lecturer-id",
                "course_unit_id": "course-unit-id",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["unassigned"])
        self.assertIn("unassigned", payload["message"].lower())


if __name__ == "__main__":
    unittest.main()
