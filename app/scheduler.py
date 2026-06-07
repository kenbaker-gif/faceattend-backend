"""
scheduler.py
APScheduler daily digest job for FaceAttend.
Wire into FastAPI lifespan in main.py.

Sends:
  - Super admin (abubaker@faceattend.app): global digest of all institutions
  - Each institution admin: their institution's events from last 24h
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.dep import supabase, supabase_admin
import app.utils.email as email_util

logger = logging.getLogger(__name__)

SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "abubaker@faceattend.app")

# EAT = UTC+3  →  8AM EAT = 5AM UTC
DIGEST_HOUR_UTC   = 5
DIGEST_MINUTE_UTC = 0


async def _fetch_events_since(hours: int = 24, institution_id: str | None = None) -> list[dict]:
    """Fetch audit log events from the last N hours, optionally scoped to an institution."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    try:
        q = (
            supabase.table("audit_logs")
            .select("*")
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(500)
        )
        if institution_id:
            q = q.eq("institution_id", institution_id)
        res = q.execute()
        return res.data or []
    except Exception as exc:
        logger.error("[digest] Failed to fetch events: %s", exc)
        return []


async def _fetch_institution_admins() -> list[dict]:
    """
    Fetch all institution admins (non-super-admin) who have email stored.
    Returns list of {institution_id, email, institution_name}.
    """
    try:
        res = (
            supabase.table("profiles")
            .select("id, institution_id, email, institutions(name)")
            .eq("is_admin", True)
            .eq("is_super_admin", False)
            .not_.is_("institution_id", "null")
            .execute()
        )
        admins = []
        for row in res.data or []:
            email = row.get("email")
            if not email:
                continue
            inst = row.get("institutions") or {}
            admins.append({
                "email":            email,
                "institution_id":   row.get("institution_id"),
                "institution_name": inst.get("name", "Your Institution"),
            })
        return admins
    except Exception as exc:
        logger.error("[digest] Failed to fetch admins: %s", exc)
        return []


async def check_expiring_subscriptions() -> None:
    """Check for subscriptions expiring in 3 days and send reminders."""
    logger.info("[subscriptions] Checking for expiring subscriptions")
    expiry_threshold = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    
    try:
        # Get institutions with subscriptions expiring soon
        res = supabase_admin.table("institutions")\
            .select("id, name, admin_email, plans, subscription_expires_at")\
            .not_.is_("subscription_expires_at", "null")\
            .lte("subscription_expires_at", expiry_threshold)\
            .gte("subscription_expires_at", datetime.now(timezone.utc).isoformat())\
            .eq("is_active", True)\
            .execute()
        
        for inst in res.data or []:
            expiry = datetime.fromisoformat(inst["subscription_expires_at"].replace("Z", "+00:00"))
            days_left = (expiry - datetime.now(timezone.utc)).days
            
            if inst.get("admin_email"):
                await email_util.send_subscription_reminder(
                    email=inst["admin_email"],
                    institution_name=inst["name"],
                    plan=inst["plans"],
                    days_left=days_left
                )
                logger.info(f"[subscriptions] Reminder sent to {inst['name']} ({days_left} days left)")
    
    except Exception as exc:
        logger.error(f"[subscriptions] Failed to check expiring subscriptions: {exc}")


async def send_daily_digests() -> None:
    """Main digest job — runs once daily at 8AM EAT."""
    logger.info("[digest] Starting daily digest job")
    date_label = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # 1. Global digest → super admin
    all_events = await _fetch_events_since(hours=24)
    if all_events:
        await email_util.send_digest(
            recipients=[SUPER_ADMIN_EMAIL],
            events=all_events,
            institution_name="All Institutions",
            date_label=date_label,
        )
        logger.info("[digest] Global digest sent (%d events)", len(all_events))
    else:
        logger.info("[digest] No events in last 24h — skipping global digest")

    # 2. Per-institution digest → each admin
    admins = await _fetch_institution_admins()
    for admin in admins:
        events = await _fetch_events_since(
            hours=24,
            institution_id=admin["institution_id"],
        )
        if not events:
            continue
        await email_util.send_digest(
            recipients=[admin["email"]],
            events=events,
            institution_name=admin["institution_name"],
            date_label=date_label,
        )
        logger.info(
            "[digest] Sent to %s for %s (%d events)",
            admin["email"], admin["institution_name"], len(events),
        )

    logger.info("[digest] Daily digest job complete")


async def process_auto_renewals():
    """Process institutions with auto-renewal enabled."""
    from app.services.billing import BillingService
    
    logger.info("[renewals] Starting auto-renewal processing")
    
    try:
        now = datetime.now(timezone.utc)
        
        # Get institutions due for renewal
        result = supabase.table("auto_renewal_settings").select("*").lte("next_renewal_date", now.isoformat()).eq("enabled", True).execute()
        
        if not result.data:
            logger.info("[renewals] No institutions due for renewal")
            return
        
        for renewal in result.data:
            institution_id = renewal['institution_id']
            
            # Get institution details
            inst = supabase.table("institutions").select("*").eq("id", institution_id).execute()
            if not inst.data:
                continue
            
            inst_data = inst.data[0]
            plan = inst_data.get('plan', 'free')
            
            if plan == 'free':
                continue  # Don't process free plans
            
            try:
                # Generate invoice
                invoice = BillingService.generate_invoice(
                    institution_id,
                    plan,
                    f"Auto-renewal: {plan} plan",
                    due_days=7
                )
                
                # Store invoice
                supabase.table("invoices").insert({
                    "id": invoice.invoice_id,
                    "institution_id": invoice.institution_id,
                    "plan": invoice.plan,
                    "amount": invoice.amount,
                    "currency": invoice.currency,
                    "issue_date": invoice.issue_date.isoformat(),
                    "due_date": invoice.due_date.isoformat(),
                    "status": "pending",
                    "description": invoice.description
                }).execute()
                
                logger.info(f"[renewals] Generated invoice for {institution_id}: {invoice.invoice_id}")
                
                # Update next renewal date (30 days from now)
                next_renewal = now + timedelta(days=30)
                supabase.table("auto_renewal_settings").update({
                    "next_renewal_date": next_renewal.isoformat()
                }).eq("institution_id", institution_id).execute()
                
            except Exception as e:
                logger.error(f"[renewals] Failed to process renewal for {institution_id}: {e}")
                continue
        
        logger.info(f"[renewals] Auto-renewal processing complete: {len(result.data)} institutions")
        
    except Exception as e:
        logger.error(f"[renewals] Auto-renewal processing failed: {e}")


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    scheduler = AsyncIOScheduler()
    
    # Daily digest at 8AM EAT (5AM UTC)
    scheduler.add_job(
        send_daily_digests,
        trigger=CronTrigger(hour=DIGEST_HOUR_UTC, minute=DIGEST_MINUTE_UTC, timezone="UTC"),
        id="daily_digest",
        name="Daily Audit Digest",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1hr late if server was down
    )
    
    # Check expiring subscriptions daily at 9AM UTC
    scheduler.add_job(
        check_expiring_subscriptions,
        trigger=CronTrigger(hour=9, minute=0, timezone="UTC"),
        id="subscription_check",
        name="Check Expiring Subscriptions",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    
    # Process auto-renewals daily at 2AM UTC
    scheduler.add_job(
        process_auto_renewals,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="auto_renewal",
        name="Process Auto-Renewals",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    
    return scheduler