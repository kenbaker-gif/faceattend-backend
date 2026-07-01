"""Test suite for reorganized codebase structure and imports."""
import pytest
from fastapi.testclient import TestClient


def test_imports_work():
    """Verify all new imports are valid."""
    from app.main import app
    from app.config import settings
    from app.middleware.security import SecurityHeadersMiddleware
    from app.models.student import StudentBase, StudentCreate
    from app.models.institution import InstitutionBase
    from app.models.attendance import AttendanceRecord
    from app.models.payment import PaymentRequest
    from app.routes.admin import students, institutions, coordinators
    from app.routes.api.v1 import router as v1_router
    from app.routes.webhooks.pesapal import router as pesapal_router
    assert app is not None
    assert settings is not None


def test_health_endpoint():
    """Verify health check works."""
    from app.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_static_files_served():
    """Verify static files are accessible."""
    from app.main import app
    client = TestClient(app)
    
    # Test HTML files
    response = client.get("/dashboard")
    assert response.status_code in [200, 307]  # 307 if redirects
    
    # Test static assets
    response = client.get("/static/css/dashboard.css")
    assert response.status_code == 200


def test_security_headers():
    """Verify security middleware is active."""
    from app.main import app
    client = TestClient(app)
    
    response = client.get("/health")
    headers = response.headers
    
    assert "x-content-type-options" in headers
    assert "x-frame-options" in headers
    assert "strict-transport-security" in headers


def test_admin_routes_mounted():
    """Verify admin routes are accessible."""
    from app.main import app
    client = TestClient(app)
    
    # Should return 401/403 without auth, not 404
    response = client.get("/admin/students")
    assert response.status_code in [401, 403, 422]


def test_api_v1_routes_mounted():
    """Verify v1 API routes are accessible."""
    from app.main import app
    client = TestClient(app)
    
    # Should return 401/403 without API key, not 404
    response = client.get("/v1/students")
    assert response.status_code in [401, 403, 422]


def test_webhook_routes_mounted():
    """Verify webhook routes are accessible."""
    from app.main import app
    client = TestClient(app)
    
    response = client.post("/webhooks/pesapal/ipn")
    # Should process, not 404
    assert response.status_code != 404


def test_config_settings():
    """Verify config loads environment variables."""
    from app.config import settings
    
    assert hasattr(settings, 'supabase_url')
    assert hasattr(settings, 'supabase_key')
    assert hasattr(settings, 'pesapal_env')
    assert hasattr(settings, 'email_from')


def test_pydantic_models():
    """Verify Pydantic models validate correctly."""
    from app.models.student import StudentCreate
    from app.models.payment import PaymentRequest
    
    # Valid student
    student = StudentCreate(
        name="Test Student",
        reg_number="TEST001",
        institution_id="uuid-here",
        course="Computer Science"
    )
    assert student.name == "Test Student"
    
    # Valid payment
    payment = PaymentRequest(
        institution_id="uuid-here",
        plan="premium",
        amount=5000
    )
    assert payment.plan == "premium"
