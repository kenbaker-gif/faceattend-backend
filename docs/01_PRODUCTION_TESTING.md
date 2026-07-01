# Production Testing Checklist

## Pre-Deployment
- [ ] Run local tests: `python3 -m pytest tests/ -v`
- [ ] Check all imports: `python3 -c "from app.main import app; print('✓ Imports OK')"`
- [ ] Verify environment variables set in `.env`
- [ ] Review `.gitignore` - ensure no secrets committed
- [ ] Update `README.md` if needed

## Deployment
- [ ] Push to main branch: `git push origin main`
- [ ] Monitor DigitalOcean build logs
- [ ] Check container starts successfully
- [ ] Verify health endpoint: `curl https://your-app/health`

## Post-Deployment Verification

### Core Functionality
- [ ] `/health` returns 200 with `{"status": "healthy"}`
- [ ] Landing page (`/`) loads correctly
- [ ] Dashboard (`/dashboard`) accessible
- [ ] Login page (`/login`) works
- [ ] OpenAPI docs (`/docs`, `/redoc`) load

### Static Assets
- [ ] `/static/css/dashboard.css` loads
- [ ] `/static/js/dashboard.js` loads
- [ ] `/static/admin_favicon.ico` loads
- [ ] All HTML files reference correct asset paths

### API Routes
- [ ] `/admin/students` returns 401 (not 404) without auth
- [ ] `/v1/students` returns 401 (not 404) without API key
- [ ] `/webhooks/pesapal/ipn` returns non-404

### Security
- [ ] `X-Content-Type-Options: nosniff` header present
- [ ] `X-Frame-Options: DENY` header present
- [ ] `Strict-Transport-Security` header present (HTTPS)
- [ ] CSP headers configured

### Billing Features (Phase 1)
- [ ] Student limits enforced per plan (free: 50, premium: 500, enterprise: unlimited)
- [ ] Subscription expiry blocks operations
- [ ] Reminder emails sent at 7 days and 1 day before expiry
- [ ] Payment webhook from Pesapal processes correctly

### Integration Tests
- [ ] Create test institution via admin API
- [ ] Add students up to plan limit
- [ ] Record attendance via mobile app
- [ ] Generate attendance summary
- [ ] Process test payment (sandbox)
- [ ] Verify email notifications

### Performance
- [ ] Response times < 200ms for API calls
- [ ] Dashboard loads in < 2 seconds
- [ ] Database queries optimized (check logs)
- [ ] No memory leaks (monitor for 24h)

### Monitoring
- [ ] Sentry receiving error reports
- [ ] Check Sentry dashboard for new errors
- [ ] Review application logs in DigitalOcean
- [ ] Set up uptime monitoring (UptimeRobot, etc.)

### Database
- [ ] Supabase connection working
- [ ] RLS policies active
- [ ] Storage bucket accessible
- [ ] Backup schedule confirmed

## Automated Verification
Run the production verification script:
```bash
./deployment/verify_production.sh https://your-app.ondigitalocean.app
```

## Rollback Plan
If critical issues found:
1. Revert to previous commit: `git revert HEAD`
2. Push: `git push origin main`
3. Monitor DigitalOcean redeploy
4. Investigate issues in staging environment

## Sign-Off
- [ ] All tests passing
- [ ] No critical errors in Sentry
- [ ] Client/stakeholder approval
- [ ] Documentation updated

**Deployed by:** _____________  
**Date:** _____________  
**Version/Commit:** _____________
