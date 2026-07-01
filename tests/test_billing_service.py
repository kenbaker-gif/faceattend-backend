"""Unit tests for Phase 2 billing service."""
import pytest
from datetime import datetime, timedelta
from app.services.billing import BillingService


class TestProration:
    """Test proration calculations."""
    
    def test_upgrade_proration(self):
        """Upgrading mid-cycle should charge difference."""
        future_date = datetime.utcnow() + timedelta(days=15)
        proration = BillingService.calculate_proration("free", "premium", future_date)
        
        assert proration.current_plan == "free"
        assert proration.new_plan == "premium"
        assert proration.days_remaining == 15
        assert proration.net_amount > 0  # Should charge
    
    def test_downgrade_proration(self):
        """Downgrading mid-cycle should credit difference."""
        future_date = datetime.utcnow() + timedelta(days=15)
        proration = BillingService.calculate_proration("premium", "free", future_date)
        
        assert proration.net_amount < 0  # Should credit/refund
    
    def test_zero_days_remaining(self):
        """Expired subscription should have zero proration."""
        past_date = datetime.utcnow() - timedelta(days=1)
        proration = BillingService.calculate_proration("premium", "enterprise", past_date)
        
        assert proration.days_remaining == 0
        assert proration.refund_amount == 0
        assert proration.charge_amount == 0


class TestPlanValidation:
    """Test plan change validation."""
    
    def test_downgrade_within_limits(self):
        """Should allow downgrade if within new limit."""
        valid, error = BillingService.validate_plan_change("premium", "free", 30)
        assert valid is True
        assert error is None
    
    def test_downgrade_exceeds_limit(self):
        """Should block downgrade if exceeds new limit."""
        valid, error = BillingService.validate_plan_change("premium", "free", 100)
        assert valid is False
        assert "Cannot downgrade" in error
        assert "100" in error
        assert "50" in error
    
    def test_upgrade_always_allowed(self):
        """Upgrades should always be allowed."""
        valid, error = BillingService.validate_plan_change("free", "premium", 100)
        assert valid is True


class TestInvoiceGeneration:
    """Test invoice generation."""
    
    def test_invoice_created_correctly(self):
        """Invoice should contain correct details."""
        invoice = BillingService.generate_invoice(
            "test-uuid-123",
            "premium",
            "Monthly subscription",
            7
        )
        
        assert invoice.institution_id == "test-uuid-123"
        assert invoice.plan == "premium"
        assert invoice.amount == 5000
        assert invoice.currency == "KES"
        assert invoice.status == "pending"
        assert invoice.description == "Monthly subscription"
        assert (invoice.due_date - invoice.issue_date).days == 7
    
    def test_invoice_id_format(self):
        """Invoice ID should follow expected format."""
        invoice = BillingService.generate_invoice("inst-123", "enterprise", "Test", 7)
        
        assert invoice.invoice_id.startswith("INV-inst-123")
        assert len(invoice.invoice_id) > 20


class TestGracePeriod:
    """Test grace period calculations."""
    
    def test_not_in_grace_period_before_expiry(self):
        """Should not be in grace period before expiry."""
        future_date = datetime.utcnow() + timedelta(days=5)
        in_grace = BillingService.is_in_grace_period(future_date)
        assert in_grace is False
    
    def test_in_grace_period_after_expiry(self):
        """Should be in grace period immediately after expiry."""
        past_date = datetime.utcnow() - timedelta(hours=1)
        in_grace = BillingService.is_in_grace_period(past_date, grace_days=3)
        assert in_grace is True
    
    def test_grace_period_expired(self):
        """Should not be in grace period after grace days."""
        past_date = datetime.utcnow() - timedelta(days=5)
        in_grace = BillingService.is_in_grace_period(past_date, grace_days=3)
        assert in_grace is False


class TestRenewalCalculations:
    """Test renewal date calculations."""
    
    def test_next_renewal_calculation(self):
        """Should correctly calculate next renewal date."""
        current_end = datetime(2025, 1, 15, 12, 0, 0)
        next_renewal = BillingService.calculate_next_renewal(current_end, 30)
        
        assert next_renewal == datetime(2025, 2, 14, 12, 0, 0)
    
    def test_custom_duration(self):
        """Should support custom renewal durations."""
        current_end = datetime(2025, 1, 1, 0, 0, 0)
        next_renewal = BillingService.calculate_next_renewal(current_end, 90)
        
        assert (next_renewal - current_end).days == 90


class TestPlanPrices:
    """Test plan pricing configuration."""
    
    def test_plan_prices_defined(self):
        """All plans should have prices defined."""
        assert BillingService.PLAN_PRICES["free"] == 0
        assert BillingService.PLAN_PRICES["premium"] == 5000
        assert BillingService.PLAN_PRICES["enterprise"] == 15000
    
    def test_student_limits_defined(self):
        """All plans should have student limits."""
        assert BillingService.STUDENT_LIMITS["free"] == 50
        assert BillingService.STUDENT_LIMITS["premium"] == 500
        assert BillingService.STUDENT_LIMITS["enterprise"] == float('inf')
