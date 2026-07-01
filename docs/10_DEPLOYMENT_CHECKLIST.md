# 🚀 DEPLOYMENT CHECKLIST

Use this checklist to deploy the complete Phase 2 billing system to production.

## ✅ Pre-Deployment (Local)

- [ ] All code committed to Git
- [ ] No syntax errors in Python files
- [ ] No console errors in JavaScript
- [ ] Environment variables configured
- [ ] Database migration SQL reviewed

## 📦 Database Migration

- [ ] Backup existing Supabase database
- [ ] Open Supabase SQL Editor
- [ ] Copy contents of `deployment/phase2_billing_migration.sql`
- [ ] Run migration (creates tables, RLS policies, indexes)
- [ ] Verify tables created:
  - [ ] `invoices`
  - [ ] `plan_change_history`
  - [ ] `auto_renewal_settings`
  - [ ] `payments` (enhanced)
- [ ] Verify columns added to `institutions`:
  - [ ] `plan`
  - [ ] `subscription_end`
  - [ ] `grace_period_start`
  - [ ] `grace_period_end`

## 🔧 Code Deployment

- [ ] Commit all changes:
  ```bash
  git add .
  git commit -m "Complete Phase 2 billing system with analytics (Steps 1-7)"
  git push origin main
  ```

- [ ] DigitalOcean App Platform auto-deploys
- [ ] Wait for build to complete (~5-10 minutes)
- [ ] Check deployment logs for errors

## 🧪 Post-Deployment Testing

### API Endpoints
- [ ] Test health check: `curl https://your-app/health`
- [ ] Test revenue metrics: `curl https://your-app/admin/analytics/revenue`
- [ ] Test invoice listing: `curl https://your-app/admin/billing/invoices/test_id`
- [ ] Access API docs: `https://your-app/docs`

### Frontend Pages
- [ ] Visit billing page: `https://your-app/billing`
  - [ ] Plan cards render correctly
  - [ ] Usage meter displays
  - [ ] Invoice table loads
  - [ ] Auto-renewal toggle works
  
- [ ] Visit analytics page: `https://your-app/analytics`
  - [ ] MRR/ARR cards display
  - [ ] Plan breakdown shows data
  - [ ] Usage table populates
  - [ ] Period selector works

### User Flows
- [ ] Create test institution in database
- [ ] Upgrade plan (Free → Premium)
  - [ ] Proration preview displays
  - [ ] Payment link generates
- [ ] View invoice history
  - [ ] Invoices listed correctly
- [ ] Download invoice PDF
  - [ ] PDF generates and downloads
  - [ ] PDF opens correctly
- [ ] Toggle auto-renewal
  - [ ] Next renewal date updates
  - [ ] Status changes

## 🔐 Security Check

- [ ] RLS policies active on all tables
- [ ] API key authentication working
- [ ] Admin routes require auth
- [ ] No PII exposed in responses
- [ ] CORS configured correctly

## 📧 Email Testing

- [ ] Test expiry reminder email (7 days before)
- [ ] Test expiry warning email (1 day before)
- [ ] Test auto-renewal invoice email
- [ ] Verify email templates render correctly

## ⏰ Scheduler Verification

- [ ] Check APScheduler is running
- [ ] Verify auto-renewal job scheduled (2AM UTC)
- [ ] Verify expiry check job scheduled (9AM UTC)
- [ ] Monitor logs for job execution

## 📊 Analytics Validation

- [ ] MRR calculation matches manual count
- [ ] Churn rate accurate for test data
- [ ] Usage percentages correct
- [ ] Payment success rate accurate

## 🔍 Browser Testing

- [ ] Chrome: Billing and analytics pages
- [ ] Firefox: All features work
- [ ] Safari: UI renders correctly
- [ ] Mobile: Responsive design works

## 📈 Monitoring Setup

- [ ] Sentry tracking errors
- [ ] DigitalOcean logs accessible
- [ ] Set up alerts for critical errors
- [ ] Monitor scheduler job failures

## 📝 Documentation Review

- [ ] README.md updated with new features
- [ ] API documentation current
- [ ] All step documentation complete
- [ ] Environment variables documented

## 🎓 Team Handoff (if applicable)

- [ ] Share documentation with team
- [ ] Demo billing dashboard
- [ ] Demo analytics dashboard
- [ ] Explain proration logic
- [ ] Review grace period behavior
- [ ] Show PDF invoice generation

## 🎉 Launch Checklist

- [ ] Announce new features to customers
- [ ] Monitor first few plan upgrades
- [ ] Watch for any error spikes
- [ ] Collect user feedback
- [ ] Plan follow-up improvements

## 📞 Support Preparation

Common issues and solutions:

**PDF generation fails**
→ Check reportlab installation in requirements.txt

**Proration incorrect**
→ Verify PLAN_PRICES constants in billing.py

**Auto-renewal not triggering**
→ Check scheduler logs, verify job is scheduled

**Grace period not working**
→ Ensure subscription_end dates are set correctly

**Analytics showing zero**
→ Verify data exists in institutions/students/payments tables

**Frontend assets not loading**
→ Check static file mounting in main.py

## ✅ Sign-Off

- [ ] All tests passing
- [ ] All features working in production
- [ ] Documentation complete
- [ ] Monitoring active
- [ ] Team trained (if applicable)

**Deployment Date**: _______________
**Deployed By**: _______________
**Production URL**: _______________

---

## 🆘 Rollback Plan

If critical issues arise:

1. **Revert code deployment**:
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Disable new features**:
   - Comment out analytics router in main.py
   - Comment out billing routes
   - Redeploy

3. **Database rollback**:
   - New tables can remain (they won't interfere)
   - Or drop tables: `DROP TABLE invoices, plan_change_history, auto_renewal_settings;`

4. **Communication**:
   - Notify users of temporary issues
   - Provide timeline for resolution

---

**Status**: ⬜ Not Started | ⏳ In Progress | ✅ Complete

Use this checklist to ensure a smooth deployment of all Phase 2 features!
