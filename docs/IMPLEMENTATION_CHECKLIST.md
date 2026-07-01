# ✅ Phase 1 Implementation Checklist

## Code Changes (Completed)

### 1. Student Limit Enforcement
- [x] Added `PLAN_LIMITS` dictionary
- [x] Created `check_student_limit()` function
- [x] Integrated into `/upload-student-face` endpoint
- [x] Returns clear upgrade message on limit reached

### 2. Subscription Expiry Tracking
- [x] Updated Pesapal IPN handler
- [x] Sets `subscription_expires_at` (+30 days)
- [x] Sets `last_payment_date` timestamp
- [x] Added datetime import for timezone handling

### 3. Subscription Validation
- [x] Updated `/check-trial/{id}` endpoint
- [x] Checks `subscription_expires_at` for paid plans
- [x] Returns `days_left` counter
- [x] Backward compatible with trial logic

### 4. Email Notifications
- [x] Added `check_expiring_subscriptions()` job
- [x] Scheduled daily at 9:00 AM UTC
- [x] Created `send_subscription_reminder()` function
- [x] Customized emails by urgency level

## Next Steps (You Need To Do)

### Database Migration
```bash
# Run in Supabase SQL Editor
□ Execute: ALTER TABLE institutions ADD COLUMN subscription_expires_at TIMESTAMPTZ;
□ Execute: ALTER TABLE institutions ADD COLUMN last_payment_date TIMESTAMPTZ;
□ Verify: SELECT * FROM institutions LIMIT 1;
```

### Testing
```bash
□ Test student limit (try adding 51st student on trial)
□ Test payment flow (verify expiry date gets set)
□ Test subscription check endpoint
□ Wait for 9AM UTC or manually test email function
```

### Deployment
```bash
□ Review all changes: git diff
□ Commit: git add . && git commit -m "feat: billing phase 1"
□ Push to production: git push origin main
□ Monitor logs for errors
□ Test in production environment
```

### Configuration
```bash
□ Verify ZOHO_SMTP_USER in .env
□ Verify ZOHO_REFRESH_TOKEN in .env
□ Test email sending manually
□ Check scheduler logs for job registration
```

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `app/routes/admin_students.py` | Student limits | +35 |
| `app/routes/pesapal_router.py` | Expiry tracking | +5 |
| `app/routes/admin_institutions.py` | Validation logic | +8 |
| `app/scheduler.py` | Expiry job | +30 |
| `app/utils/email.py` | Reminder function | +50 |
| **Total** | | **~130 LOC** |

## Documentation Created

- [x] `BILLING_ANALYSIS.md` - Full analysis and roadmap
- [x] `DATABASE_MIGRATION.md` - SQL migration guide
- [x] `PHASE1_SUMMARY.md` - Implementation details
- [x] `IMPLEMENTATION_CHECKLIST.md` - This file

## Quick Test Commands

```bash
# 1. Check student limit
curl -X POST https://your-api.com/upload-student-face \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "student_id=test_51" \
  -F "name=Test Student" \
  -F "institution_id=YOUR_TRIAL_INSTITUTION" \
  -F "file=@face.jpg"
# Should fail with 403 if at limit

# 2. Check subscription status
curl https://your-api.com/check-trial/YOUR_INSTITUTION_ID
# Should return days_left if paid subscription

# 3. Check scheduler logs
grep -i "subscription" /var/log/your-app.log
```

## Expected Behavior

### Before Payment
- Trial institutions: Limited to 50 students
- Can add students until limit reached
- `check-trial` returns trial status

### After Payment
- `subscription_expires_at` set to +30 days
- Student limit increases to plan tier
- `check-trial` returns days remaining

### At Expiry - 3 days
- Email reminder sent automatically
- Dashboard should show warning

### At Expiry
- `check-trial` returns `active: false`
- Email notification sent
- Users can still login but see message

## Rollback Plan

If anything breaks:

```bash
# 1. Disable student limit check
# Comment line 64 in app/routes/admin_students.py:
# check_student_limit(effective_institution_id)

# 2. Disable subscription check
# Comment lines in app/scheduler.py:
# Remove check_expiring_subscriptions job

# 3. Database rollback (if needed)
ALTER TABLE institutions 
DROP COLUMN subscription_expires_at,
DROP COLUMN last_payment_date;
```

## Success Metrics

After 1 week in production:

- [ ] 0 errors related to student limits
- [ ] X payment renewals tracked successfully  
- [ ] Y reminder emails sent
- [ ] Z institutions upgraded after reminder
- [ ] No customer complaints about enforcement

---

**Status:** ✅ Code Complete - Ready for Database Migration & Testing
**Risk:** 🟢 Low (backward compatible, soft enforcement)
**Time to Deploy:** ~30 minutes (including DB migration)
