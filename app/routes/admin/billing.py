"""Admin billing routes for plan management and invoicing."""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta
from typing import List
from app.dep import supabase_admin, check_admin, _bool_flag
from app.models.billing import (
    PlanUpgradeRequest, PlanUpgradeResponse,
    ProrationCalculation, Invoice, InvoiceCreate,
    PaymentHistory
)
from app.services.billing import BillingService
from app.services.invoice_pdf import InvoicePDFGenerator

router = APIRouter(prefix="/admin/billing", tags=["admin-billing"])


def _get_profile(user):
    p = supabase_admin.table("profiles") \
        .select("institution_id, is_super_admin, role") \
        .eq("id", user.id).single().execute().data or {}
    return p


def _check_institution_access(user, institution_id: str):
    """Ensure user can access this institution."""
    p = _get_profile(user)
    is_super = _bool_flag(p.get("is_super_admin")) or p.get("role") == "super_admin"
    if not is_super and p.get("institution_id") != institution_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return is_super


@router.post("/upgrade", response_model=PlanUpgradeResponse)
async def upgrade_plan(request: PlanUpgradeRequest, user=Depends(check_admin)):
    _check_institution_access(user, request.institution_id)

    inst_result = supabase_admin.table("institutions").select("*").eq("id", request.institution_id).execute()
    if not inst_result.data:
        raise HTTPException(404, "Institution not found")

    institution = inst_result.data[0]
    current_plan = institution.get("plan", "free")
    subscription_end = institution.get("subscription_end")

    student_count = supabase_admin.table("students").select("id", count="exact") \
        .eq("institution_id", request.institution_id).execute().count or 0

    valid, error = BillingService.validate_plan_change(current_plan, request.new_plan, student_count)
    if not valid:
        raise HTTPException(400, error)

    proration = None
    payment_required = False
    payment_link = None

    if subscription_end:
        sub_end_dt = datetime.fromisoformat(subscription_end.replace('Z', '+00:00'))
        proration = BillingService.calculate_proration(current_plan, request.new_plan, sub_end_dt)
        if proration.net_amount > 0:
            payment_required = True
            payment_link = f"/payments/subscribe?plan={request.new_plan}&amount={proration.net_amount}"

    new_subscription_end = datetime.utcnow() + timedelta(days=30)
    supabase_admin.table("institutions").update({
        "plan": request.new_plan,
        "subscription_end": new_subscription_end.isoformat(),
    }).eq("id", request.institution_id).execute()

    return PlanUpgradeResponse(
        success=True,
        message=f"Successfully changed from {current_plan} to {request.new_plan}",
        new_plan=request.new_plan,
        effective_date=datetime.utcnow(),
        prorated_amount=proration.net_amount if proration else None,
        payment_required=payment_required,
        payment_link=payment_link
    )


@router.get("/proration/{institution_id}")
async def calculate_proration(institution_id: str, new_plan: str, user=Depends(check_admin)):
    _check_institution_access(user, institution_id)

    inst_result = supabase_admin.table("institutions").select("*").eq("id", institution_id).execute()
    if not inst_result.data:
        raise HTTPException(404, "Institution not found")

    institution = inst_result.data[0]
    current_plan = institution.get("plan", "free")
    subscription_end = institution.get("subscription_end")

    if not subscription_end:
        raise HTTPException(400, "No active subscription")

    sub_end_dt = datetime.fromisoformat(subscription_end.replace('Z', '+00:00'))
    return BillingService.calculate_proration(current_plan, new_plan, sub_end_dt)


@router.post("/invoices", response_model=Invoice)
async def create_invoice(request: InvoiceCreate, user=Depends(check_admin)):
    _check_institution_access(user, request.institution_id)

    invoice = BillingService.generate_invoice(
        request.institution_id, request.plan,
        request.description, request.due_days
    )
    supabase_admin.table("invoices").insert({
        "id": invoice.invoice_id,
        "institution_id": invoice.institution_id,
        "plan": invoice.plan,
        "amount": invoice.amount,
        "currency": invoice.currency,
        "issue_date": invoice.issue_date.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "status": invoice.status,
        "description": invoice.description
    }).execute()

    return invoice


@router.get("/invoices/{institution_id}", response_model=List[Invoice])
async def get_invoices(institution_id: str, user=Depends(check_admin)):
    _check_institution_access(user, institution_id)

    result = supabase_admin.table("invoices").select("*") \
        .eq("institution_id", institution_id).order("issue_date", desc=True).execute()

    return [
        Invoice(
            invoice_id=inv["id"],
            institution_id=inv["institution_id"],
            plan=inv["plan"],
            amount=inv["amount"],
            currency=inv.get("currency", "KES"),
            issue_date=datetime.fromisoformat(inv["issue_date"].replace('Z', '+00:00')),
            due_date=datetime.fromisoformat(inv["due_date"].replace('Z', '+00:00')),
            status=inv["status"],
            description=inv["description"]
        )
        for inv in result.data
    ]


@router.get("/payment-history/{institution_id}", response_model=List[PaymentHistory])
async def get_payment_history(institution_id: str, user=Depends(check_admin)):
    _check_institution_access(user, institution_id)

    result = supabase_admin.table("payments").select("*") \
        .eq("institution_id", institution_id).order("payment_date", desc=True).execute()

    return [
        PaymentHistory(
            payment_id=p["id"],
            institution_id=p["institution_id"],
            amount=p["amount"],
            currency=p.get("currency", "KES"),
            plan=p.get("plan", "unknown"),
            payment_date=datetime.fromisoformat(p["payment_date"].replace('Z', '+00:00')),
            payment_method=p.get("payment_method", "pesapal"),
            transaction_id=p.get("transaction_id", ""),
            status=p.get("status", "success")
        )
        for p in result.data
    ]


@router.get("/invoices/{institution_id}/{invoice_id}/pdf")
async def download_invoice_pdf(institution_id: str, invoice_id: str, user=Depends(check_admin)):
    _check_institution_access(user, institution_id)

    inv_result = supabase_admin.table("invoices").select("*") \
        .eq("id", invoice_id).eq("institution_id", institution_id).execute()
    if not inv_result.data:
        raise HTTPException(404, "Invoice not found")

    invoice = inv_result.data[0]
    inst_result = supabase_admin.table("institutions").select("name").eq("id", institution_id).execute()
    institution_name = inst_result.data[0]["name"] if inst_result.data else "Unknown"

    invoice_data = {
        "invoice_number": invoice["id"][:8].upper(),
        "created_at": datetime.fromisoformat(invoice["issue_date"].replace('Z', '+00:00')).strftime("%Y-%m-%d"),
        "due_date": datetime.fromisoformat(invoice["due_date"].replace('Z', '+00:00')).strftime("%Y-%m-%d"),
        "institution_name": institution_name,
        "institution_id": institution_id,
        "description": invoice["description"],
        "amount": invoice["amount"],
        "currency": invoice.get("currency", "KES"),
        "status": invoice["status"],
        "proration_details": invoice.get("proration_details")
    }

    pdf_buffer = InvoicePDFGenerator.generate(invoice_data)
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice_id[:8]}.pdf"}
    )