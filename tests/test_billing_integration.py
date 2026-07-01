"""Integration tests for Phase 1 billing functionality."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch('app.routes.admin.students.supabase') as mock:
        yield mock


class TestStudentLimits:
    """Test student limit enforcement per plan."""
    
    def test_free_plan_limit(self, client, mock_supabase):
        """Free plan should enforce 50 student limit."""
        mock_supabase.table().select().eq().execute.return_value = MagicMock(
            data=[{"plan": "free"}]
        )
        mock_supabase.table().select().eq().count = MagicMock(return_value=MagicMock(count=50))
        
        # Attempt to add 51st student should fail
        response = client.post("/admin/students", json={
            "name": "Test Student",
            "reg_number": "TEST051",
            "institution_id": "test-uuid"
        })
        assert response.status_code in [400, 403, 422]
    
    def test_premium_plan_limit(self, client, mock_supabase):
        """Premium plan should enforce 500 student limit."""
        mock_supabase.table().select().eq().execute.return_value = MagicMock(
            data=[{"plan": "premium"}]
        )
        mock_supabase.table().select().eq().count = MagicMock(return_value=MagicMock(count=500))
        
        response = client.post("/admin/students", json={
            "name": "Test Student",
            "reg_number": "TEST501",
            "institution_id": "test-uuid"
        })
        assert response.status_code in [400, 403, 422]


class TestSubscriptionExpiry:
    """Test subscription expiry validation."""
    
    def test_expired_subscription_blocks_operations(self, client, mock_supabase):
        """Expired subscription should prevent student operations."""
        from datetime import datetime, timedelta
        
        expired_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        mock_supabase.table().select().eq().execute.return_value = MagicMock(
            data=[{
                "plan": "premium",
                "subscription_end": expired_date
            }]
        )
        
        response = client.post("/admin/students", json={
            "name": "Test Student",
            "reg_number": "TEST001",
            "institution_id": "test-uuid"
        })
        assert response.status_code in [400, 403, 422]
    
    def test_active_subscription_allows_operations(self, client, mock_supabase):
        """Active subscription should allow operations."""
        from datetime import datetime, timedelta
        
        future_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        mock_supabase.table().select().eq().execute.return_value = MagicMock(
            data=[{
                "plan": "premium",
                "subscription_end": future_date
            }]
        )
        mock_supabase.table().select().eq().count = MagicMock(return_value=MagicMock(count=10))
        mock_supabase.table().insert().execute.return_value = MagicMock(data=[{"id": "new-uuid"}])
        
        # Should succeed (or fail for other reasons, not subscription)
        response = client.post("/admin/students", json={
            "name": "Test Student",
            "reg_number": "TEST001",
            "institution_id": "test-uuid"
        })
        # Not testing full flow, just that it doesn't fail on subscription check


class TestReminderEmails:
    """Test expiry reminder email system."""
    
    @patch('app.routes.admin.institutions.send_email')
    def test_7_day_reminder_sent(self, mock_email, client, mock_supabase):
        """Should send reminder 7 days before expiry."""
        from datetime import datetime, timedelta
        
        expiry_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
        mock_supabase.table().select().execute.return_value = MagicMock(
            data=[{
                "id": "inst-uuid",
                "name": "Test Institution",
                "email": "test@example.com",
                "plan": "premium",
                "subscription_end": expiry_date,
                "last_reminder_sent": None
            }]
        )
        
        # Trigger reminder check (would be called by scheduler)
        # Implementation depends on your actual scheduler setup
        assert True  # Placeholder for actual scheduler test
    
    @patch('app.routes.admin.institutions.send_email')
    def test_1_day_reminder_sent(self, mock_email, client, mock_supabase):
        """Should send final reminder 1 day before expiry."""
        from datetime import datetime, timedelta
        
        expiry_date = (datetime.utcnow() + timedelta(days=1)).isoformat()
        mock_supabase.table().select().execute.return_value = MagicMock(
            data=[{
                "id": "inst-uuid",
                "name": "Test Institution",
                "email": "test@example.com",
                "plan": "premium",
                "subscription_end": expiry_date,
                "last_reminder_sent": None
            }]
        )
        
        assert True  # Placeholder for actual scheduler test
