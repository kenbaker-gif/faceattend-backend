"""PDF invoice generation service using ReportLab."""
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors


class InvoicePDFGenerator:
    """Generate professional PDF invoices."""
    
    @staticmethod
    def generate(invoice_data: dict) -> BytesIO:
        """Generate invoice PDF and return as BytesIO buffer."""
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Header
        c.setFont("Helvetica-Bold", 24)
        c.drawString(1*inch, height - 1*inch, "INVOICE")
        
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, height - 1.3*inch, "FaceAttend - Smart Attendance System")
        c.drawString(1*inch, height - 1.5*inch, "Email: support@faceattend.app")
        
        # Invoice details (right aligned)
        c.drawRightString(width - 1*inch, height - 1*inch, f"Invoice #: {invoice_data['invoice_number']}")
        c.drawRightString(width - 1*inch, height - 1.2*inch, f"Date: {invoice_data['created_at']}")
        c.drawRightString(width - 1*inch, height - 1.4*inch, f"Due: {invoice_data['due_date']}")
        
        # Bill to section
        y = height - 2.5*inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, y, "Bill To:")
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, y - 0.2*inch, invoice_data['institution_name'])
        c.drawString(1*inch, y - 0.4*inch, f"Institution ID: {invoice_data['institution_id']}")
        
        # Items table
        y = height - 4*inch
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1*inch, y, "Description")
        c.drawRightString(width - 1*inch, y, "Amount")
        
        # Line under header
        y -= 0.1*inch
        c.line(1*inch, y, width - 1*inch, y)
        
        # Item details
        y -= 0.3*inch
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, y, invoice_data['description'])
        c.drawRightString(width - 1*inch, y, f"{invoice_data['currency']} {invoice_data['amount']:,.2f}")
        
        # If proration details exist
        if invoice_data.get('proration_details'):
            y -= 0.3*inch
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.grey)
            c.drawString(1.2*inch, y, invoice_data['proration_details'])
            c.setFillColor(colors.black)
        
        # Total section
        y -= 0.5*inch
        c.line(width - 3*inch, y, width - 1*inch, y)
        y -= 0.3*inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(width - 3*inch, y, "Total:")
        c.drawRightString(width - 1*inch, y, f"{invoice_data['currency']} {invoice_data['amount']:,.2f}")
        
        # Status badge
        y -= 0.5*inch
        status = invoice_data['status'].upper()
        status_color = colors.green if status == 'PAID' else colors.orange if status == 'PENDING' else colors.red
        c.setFillColor(status_color)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1*inch, y, f"Status: {status}")
        c.setFillColor(colors.black)
        
        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawCentredString(width/2, 1*inch, "Thank you for your business!")
        c.drawCentredString(width/2, 0.8*inch, "For support, contact: support@faceattend.app")
        
        c.save()
        buffer.seek(0)
        return buffer
