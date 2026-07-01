"""Unit tests for PDF invoice generation."""
import pytest
from datetime import datetime
from app.services.invoice_pdf import InvoicePDFGenerator


def test_generate_pdf():
    """Test basic PDF generation."""
    invoice_data = {
        "invoice_number": "INV12345",
        "created_at": "2026-06-04",
        "due_date": "2026-07-04",
        "institution_name": "Test University",
        "institution_id": "inst_123",
        "description": "Premium Plan - Monthly Subscription",
        "amount": 3000.00,
        "currency": "KES",
        "status": "pending",
        "proration_details": None
    }
    
    pdf_buffer = InvoicePDFGenerator.generate(invoice_data)
    
    assert pdf_buffer is not None
    assert pdf_buffer.getvalue()[:4] == b'%PDF'  # PDF header


def test_generate_pdf_with_proration():
    """Test PDF generation with proration details."""
    invoice_data = {
        "invoice_number": "INV67890",
        "created_at": "2026-06-04",
        "due_date": "2026-07-04",
        "institution_name": "Another School",
        "institution_id": "inst_456",
        "description": "Enterprise Plan Upgrade",
        "amount": 5000.00,
        "currency": "KES",
        "status": "paid",
        "proration_details": "Prorated for 15 days remaining (Premium → Enterprise)"
    }
    
    pdf_buffer = InvoicePDFGenerator.generate(invoice_data)
    
    assert pdf_buffer is not None
    assert len(pdf_buffer.getvalue()) > 1000  # Reasonable PDF size
