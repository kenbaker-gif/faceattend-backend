"""Unit tests for analytics service."""
import pytest
from unittest.mock import MagicMock
from app.services.analytics import AnalyticsService


def test_calculate_mrr():
    """Test MRR calculation."""
    mock_supabase = MagicMock()
    mock_supabase.table().select().execute.return_value.data = [
        {"plan": "free"},
        {"plan": "premium"},
        {"plan": "premium"},
        {"plan": "enterprise"}
    ]
    
    result = AnalyticsService.calculate_mrr(mock_supabase)
    
    assert result["mrr"] == 16000  # 2*3000 + 1*10000
    assert result["arr"] == 192000
    assert result["total_institutions"] == 4
    assert result["plan_breakdown"]["premium"]["count"] == 2


def test_calculate_churn():
    """Test churn rate calculation."""
    mock_supabase = MagicMock()
    
    # Plan change history
    changes_mock = MagicMock()
    changes_mock.data = [
        {"from_plan": "premium", "to_plan": "free"},
        {"from_plan": "enterprise", "to_plan": "premium"}
    ]
    
    # Total institutions
    institutions_mock = MagicMock()
    institutions_mock.count = 100
    
    mock_supabase.table().select().gte().execute.return_value = changes_mock
    mock_supabase.table().select().execute.return_value = institutions_mock
    
    result = AnalyticsService.calculate_churn(mock_supabase, 30)
    
    assert result["churned_count"] == 2
    assert result["churn_rate"] == 2.0  # 2/100 * 100


def test_get_usage_trends():
    """Test usage trends calculation."""
    mock_supabase = MagicMock()
    
    # Institutions
    inst_mock = MagicMock()
    inst_mock.data = [
        {"id": "1", "name": "School A", "plan": "premium"},
        {"id": "2", "name": "School B", "plan": "free"}
    ]
    
    # Student counts
    students_mock_1 = MagicMock()
    students_mock_1.count = 450
    students_mock_2 = MagicMock()
    students_mock_2.count = 40
    
    mock_supabase.table().select().execute.return_value = inst_mock
    mock_supabase.table().select().eq().execute.side_effect = [students_mock_1, students_mock_2]
    
    result = AnalyticsService.get_usage_trends(mock_supabase)
    
    assert len(result) == 2
    assert result[0]["students"] == 450
    assert result[0]["utilization"] == 90.0  # 450/500


def test_payment_metrics():
    """Test payment success rate."""
    mock_supabase = MagicMock()
    
    payments_mock = MagicMock()
    payments_mock.data = [
        {"status": "success"},
        {"status": "success"},
        {"status": "failed"}
    ]
    
    mock_supabase.table().select().gte().execute.return_value = payments_mock
    
    result = AnalyticsService.get_payment_metrics(mock_supabase, 30)
    
    assert result["total_payments"] == 3
    assert result["successful"] == 2
    assert result["failed"] == 1
    assert result["success_rate"] == 66.67
