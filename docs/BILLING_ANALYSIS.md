# 💰 FaceAttend Billing Analysis & Recommendations

## 📊 Current Billing Setup

### Pricing Structure
```
Starter:    $49/month  — up to 500 students
Growth:     $99/month  — up to 2,000 students
Pro:        $199/month — up to 5,000 students
Enterprise: Custom     — Contact sales
```

### Payment Flow
1. **Payment Gateway**: Pesapal (African payment processor)
2. **One-time Payments**: No recurring billing implemented
3. **Plan Assignment**: Manual upgrade via IPN (Instant Payment Notification)
4. **Trial System**: Institutions start on "trial" plan with `trial_ends_at` date

### Technical Implementation

#### Pesapal Integration (`app/routes/pesapal_router.py`)
- **Endpoint**: `/api/cart/create-cart` — initiates payment
- **IPN Handler**: `/api/cart/ipn` — receives payment confirmation
- **Flow**:
  1. User selects plan → creates order → redirects to Pesapal
  2. User completes payment
  3. Pesapal sends IPN callback
  4. Backend updates `institutions.plans` field
  5. Order deleted from `pesapal_orders` table

#### Institution Status Check (`app/routes/admin_institutions.py`)
```python
PAID_PLANS = {"paid", "starter", "growth", "pro", "enterprise"}

# Logic:
- If plans in PAID_PLANS → always active
- If plans == "trial" → check trial_ends_at expiry
- If is_active == False → suspended
```

---

## ⚠️ Current Issues

### 1. **No Recurring Billing**
- Users pay once, get lifetime access
- No monthly/annual renewals
- No subscription management

### 2. **No Student Limit Enforcement**
- Plans advertise limits (500, 2000, 5000 students)
- **No code enforces these limits**
- Institutions can exceed their plan capacity

### 3. **Manual Plan Management**
- No self-service upgrade/downgrade
- No billing portal
- No invoicing system

### 4. **Limited Payment Methods**
- Only Pesapal (Africa-focused)
- No Stripe, PayPal, or global options

### 5. **No Revenue Tracking**
- No MRR (Monthly Recurring Revenue) calculation
- No churn metrics
- No payment history dashboard

### 6. **No Grace Period**
- Trial expires → immediate lockout
- No "past due" state

---

## 🚀 Recommended Improvements

### Phase 1: Critical Fixes (Week 1-2)

#### 1.1 Implement Student Limits
```python
# In admin_students.py or v1_api.py before adding students:

PLAN_LIMITS = {
    "trial": 50,
    "starter": 500,
    "growth": 2000,
    "pro": 5000,
    "enterprise": 999999  # unlimited
}

async def check_student_limit(institution_id: str):
    # Get current student count
    count = supabase_admin.table("students")\
        .select("id", count="exact")\
        .eq("institution_id", institution_id)\
        .execute()
    
    # Get institution plan
    inst = supabase_admin.table("institutions")\
        .select("plans")\
        .eq("id", institution_id)\
        .single().execute()
    
    plan = inst.data.get("plans", "trial")
    limit = PLAN_LIMITS.get(plan, 50)
    
    if count.count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Student limit reached ({limit}). Upgrade your plan."
        )
```

#### 1.2 Add Subscription Expiry Tracking
```sql
-- Add to institutions table:
ALTER TABLE institutions ADD COLUMN subscription_expires_at TIMESTAMPTZ;
ALTER TABLE institutions ADD COLUMN last_payment_date TIMESTAMPTZ;
ALTER TABLE institutions ADD COLUMN payment_status TEXT DEFAULT 'trial';
```

```python
# payment_status: 'trial', 'active', 'past_due', 'cancelled', 'suspended'
```

### Phase 2: Recurring Billing (Week 3-4)

#### 2.1 Add Subscription Management Table
```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id) ON DELETE CASCADE,
    plan TEXT NOT NULL,
    status TEXT NOT NULL, -- active, cancelled, past_due
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    amount DECIMAL(10,2),
    currency TEXT DEFAULT 'USD',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id),
    subscription_id UUID REFERENCES subscriptions(id),
    amount DECIMAL(10,2),
    currency TEXT,
    status TEXT, -- success, failed, pending, refunded
    payment_method TEXT,
    transaction_id TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 2.2 Background Job for Renewals
```python
# Add to scheduler.py
from datetime import timedelta

@scheduler.scheduled_job('cron', hour=0, minute=0)
async def check_subscription_renewals():
    """Check for subscriptions expiring in 3 days and send reminders."""
    expiring_soon = supabase_admin.table("subscriptions")\
        .select("*, institutions!inner(name, admin_email)")\
        .eq("status", "active")\
        .gte("current_period_end", datetime.now())\
        .lte("current_period_end", datetime.now() + timedelta(days=3))\
        .execute()
    
    for sub in expiring_soon.data:
        # Send renewal reminder email
        send_renewal_reminder(sub)

@scheduler.scheduled_job('cron', hour=1, minute=0)
async def process_expired_subscriptions():
    """Mark expired subscriptions as past_due."""
    expired = supabase_admin.table("subscriptions")\
        .select("*")\
        .eq("status", "active")\
        .lt("current_period_end", datetime.now())\
        .execute()
    
    for sub in expired.data:
        supabase_admin.table("subscriptions")\
            .update({"status": "past_due"})\
            .eq("id", sub["id"])\
            .execute()
        
        # Grace period: 7 days before suspension
        supabase_admin.table("institutions")\
            .update({"payment_status": "past_due"})\
            .eq("id", sub["institution_id"])\
            .execute()
```

### Phase 3: Better Payment Gateways (Month 2)

#### 3.1 Add Stripe Integration
**Why?**
- Global coverage (180+ countries)
- Built-in subscription management
- Automatic invoicing
- Customer portal
- Dunning management
- Support for all major payment methods

**Implementation:**
```bash
pip install stripe
```

```python
# app/routes/stripe_router.py
import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

STRIPE_PLANS = {
    "starter": "price_xxxxxxxxxxxxx",    # Stripe Price ID
    "growth": "price_yyyyyyyyyyyyy",
    "pro": "price_zzzzzzzzzzzzz"
}

@router.post("/stripe/create-subscription")
async def create_stripe_subscription(payload: SubscriptionRequest):
    # Create Stripe customer
    customer = stripe.Customer.create(
        email=payload.email,
        metadata={"institution_id": payload.institution_id}
    )
    
    # Create subscription
    subscription = stripe.Subscription.create(
        customer=customer.id,
        items=[{"price": STRIPE_PLANS[payload.plan]}],
        payment_behavior='default_incomplete',
        expand=['latest_invoice.payment_intent']
    )
    
    return {
        "subscription_id": subscription.id,
        "client_secret": subscription.latest_invoice.payment_intent.client_secret
    }

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    event = stripe.Webhook.construct_event(
        payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
    )
    
    if event.type == 'invoice.payment_succeeded':
        # Renew subscription
        subscription_id = event.data.object.subscription
        institution_id = event.data.object.metadata.get("institution_id")
        
        # Update subscription in DB
        ...
    
    elif event.type == 'invoice.payment_failed':
        # Handle failed payment
        ...
    
    return {"status": "ok"}
```

#### 3.2 Pricing Recommendations

**Current Issues:**
- Flat monthly pricing doesn't scale well
- Large institutions subsidize small ones
- No annual discount incentive

**Better Model:**

```python
# Tiered + Usage-based pricing
PRICING_MODEL = {
    "starter": {
        "base_monthly": 49,
        "base_annual": 470,  # ~20% discount
        "included_students": 500,
        "overage_per_student": 0.10,  # $0.10/student/month over limit
        "features": ["basic_reports", "email_support"]
    },
    "growth": {
        "base_monthly": 99,
        "base_annual": 950,
        "included_students": 2000,
        "overage_per_student": 0.05,
        "features": ["advanced_reports", "priority_support", "api_access"]
    },
    "pro": {
        "base_monthly": 199,
        "base_annual": 1910,
        "included_students": 5000,
        "overage_per_student": 0.03,
        "features": ["custom_reports", "dedicated_support", "whitelabel", "sso"]
    },
    "enterprise": {
        "base_monthly": "custom",
        "included_students": "unlimited",
        "features": ["everything", "sla", "custom_integrations"]
    }
}
```

**Benefits:**
- Annual plans increase customer lifetime value
- Overage fees make pricing fair and scalable
- Clear feature differentiation justifies price jumps

### Phase 4: Billing Dashboard (Month 2)

#### 4.1 Admin Billing Portal Features
```javascript
// Add to dashboard.js
async function renderBillingSection() {
    // Current plan & usage
    // Payment history
    // Upgrade/downgrade buttons
    // Invoice downloads
    // Payment method management
}
```

#### 4.2 Super Admin Revenue Dashboard
```javascript
// Metrics to track:
- Monthly Recurring Revenue (MRR)
- Annual Recurring Revenue (ARR)
- Customer Lifetime Value (LTV)
- Churn rate
- Active subscriptions by plan
- Trial conversion rate
- Revenue per institution
```

---

## 📈 Pricing Strategy Analysis

### Competitive Positioning

**Similar SaaS Products:**
- **Clockify** (time tracking): $10-20/user/month
- **BambooHR** (HR): $6-8/employee/month
- **Gusto** (payroll): $40 base + $6/person
- **TSheets** (attendance): $8/user/month

**Your current pricing:**
- Starter: $49 ÷ 500 = **$0.098/student/month** ✅ Competitive
- Growth: $99 ÷ 2000 = **$0.0495/student/month** ✅ Very competitive
- Pro: $199 ÷ 5000 = **$0.0398/student/month** ✅ Excellent value

### Recommended Adjustments

#### Option 1: Per-User Pricing (SaaS Standard)
```
$2/student/month with minimum:
- Minimum 25 students: $50/month
- 100 students: $200/month
- 500 students: $1,000/month
- 1000+ students: Volume discount tiers
```
**Pros:** Scales with customer value  
**Cons:** May be expensive for large schools

#### Option 2: Tiered + Volume Discounts (Recommended)
```
Tier 1 (0-100 students):    $1.50/student/month ($150 minimum)
Tier 2 (101-500 students):  $1.00/student/month
Tier 3 (501-2000 students): $0.50/student/month
Tier 4 (2001+ students):    $0.25/student/month
```
**Pros:** Fair, scalable, incentivizes growth  
**Cons:** Complex billing calculations

#### Option 3: Hybrid (Current + Overages) — **RECOMMENDED**
```
Keep your current pricing but add:
- Overage charges beyond limits
- Annual discount (15-20%)
- Add-ons (extra storage, API calls, etc.)

Example:
Starter: $49/month (500 students) → $59/month (600 students)
         Or $470/year (save $118)
```
**Pros:** Familiar model, adds flexibility, increases ARPU  
**Cons:** None significant

---

## 🎯 Implementation Roadmap

### Week 1-2: Immediate Fixes
- [ ] Add student limit enforcement
- [ ] Implement subscription expiry tracking
- [ ] Add grace period logic (7 days)
- [ ] Create payment_history table
- [ ] Email notifications for expiring trials

### Week 3-4: Recurring Billing
- [ ] Add subscriptions table
- [ ] Background job for renewal checks
- [ ] Automatic suspension after grace period
- [ ] Email reminders (3 days, 1 day, expired)

### Month 2: Stripe Integration
- [ ] Set up Stripe account
- [ ] Create products/prices in Stripe
- [ ] Implement Stripe subscription flow
- [ ] Add webhook handler
- [ ] Customer portal for payment methods
- [ ] Invoice generation

### Month 3: Enhanced Features
- [ ] Usage-based overage billing
- [ ] Annual subscription option
- [ ] Self-service upgrade/downgrade
- [ ] Billing dashboard for institutions
- [ ] Revenue analytics for super admin
- [ ] Dunning management (failed payments)

### Month 4: Scale & Optimize
- [ ] Multi-currency support
- [ ] Tax calculation (Stripe Tax)
- [ ] Usage metering and reporting
- [ ] Proration for plan changes
- [ ] Referral/affiliate system
- [ ] Enterprise custom pricing workflow

---

## 💡 Quick Wins (Implement Today)

### 1. Add Student Limit Check
File: `app/routes/admin_students.py` and `app/routes/v1_api.py`

Before any student creation, add:
```python
# Check plan limits before adding student
plan_limits = {"trial": 50, "starter": 500, "growth": 2000, "pro": 5000, "enterprise": 999999}
count_result = supabase_admin.table("students").select("id", count="exact").eq("institution_id", institution_id).execute()
inst_result = supabase_admin.table("institutions").select("plans").eq("id", institution_id).single().execute()
plan = inst_result.data.get("plans", "trial")
if count_result.count >= plan_limits.get(plan, 50):
    raise HTTPException(status_code=403, detail=f"Student limit reached. Please upgrade your plan.")
```

### 2. Update Trial Logic
Add subscription expiry field:
```python
# When IPN confirms payment, set expiry to +30 days
from datetime import datetime, timedelta
expiry = datetime.now() + timedelta(days=30)
supabase_admin.table("institutions").update({
    "plans": plan,
    "subscription_expires_at": expiry.isoformat(),
    "last_payment_date": datetime.now().isoformat()
}).eq("id", institution_id).execute()
```

### 3. Add Expiry Check Middleware
```python
# app/dep.py or middleware
async def check_subscription_active(institution_id: str):
    inst = supabase_admin.table("institutions").select("subscription_expires_at, plans").eq("id", institution_id).single().execute()
    
    if inst.data.get("plans") in {"trial", "paid", "starter", "growth", "pro", "enterprise"}:
        expiry = inst.data.get("subscription_expires_at")
        if expiry:
            if datetime.fromisoformat(expiry.replace("Z", "+00:00")) < datetime.now():
                raise HTTPException(status_code=402, detail="Subscription expired. Please renew.")
```

---

## 🔗 Resources

- [Stripe Subscription Docs](https://stripe.com/docs/billing/subscriptions/overview)
- [SaaS Pricing Guide](https://www.priceintelligently.com/hubfs/Price-Intelligently-SaaS-Pricing-Strategy.pdf)
- [Pesapal API Docs](https://developer.pesapal.com/)
- [Dunning Management Best Practices](https://stripe.com/guides/dunning-management)

---

## 📊 Expected Impact

| Improvement | Time | Impact | Priority |
|------------|------|--------|----------|
| Student limits | 4h | High (prevents abuse) | 🔴 Critical |
| Subscription expiry | 8h | High (recurring revenue) | 🔴 Critical |
| Stripe integration | 40h | Very High (global sales) | 🟡 High |
| Annual plans | 16h | Medium (increase LTV) | 🟢 Medium |
| Usage tracking | 24h | Medium (fair pricing) | 🟢 Medium |
| Billing dashboard | 32h | Medium (reduce support) | 🟢 Medium |

**Total estimated effort:** 3-4 weeks for full implementation  
**Potential revenue impact:** 2-3x increase in first year

---

Let me know which phase you'd like to implement first! 🚀
