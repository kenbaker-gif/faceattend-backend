# Audit Report - 2026-07-19

## Scope
This report captures the diff-based audit performed today for recent RLS/RBAC/dashboard changes, focused on super_admin behavior (profiles.is_super_admin = true).

## Method Used
- Reviewed git history and diffs for:
  - deployment SQL migrations
  - static/js/dashboard.js
  - backend FastAPI routes and role helpers
- Inspected commit-level changes for key commits:
  - ea8e895
  - 0cc7bf1
  - a669378
  - ef5e99d
  - 4a609fc
- Compared committed history vs current working-tree changes.

## Important Repository Constraint
- admin_screen.dart is not present in this repository/workspace, so no local git diff could be produced for that file.
- deployment/tiered_super_admin_access.sql and deployment/dept_scoped_access.sql are present in the workspace, but did not resolve to usable commit history in this branch, so exact old/new policy text for those two files cannot be fully reconstructed from git in this repo alone.

## 1) Commits Identified (RLS/RBAC/Billing/Super Admin)

### Primary commits affecting dashboard/backend role behavior
- ea8e895: Large refactor introducing dashboard structure and billing stack.
- 0cc7bf1: Dashboard/auth follow-up; role/login-related handling updates.
- a669378: Added shared auth-link logic and dashboard wiring updates.
- ef5e99d: Backend RBAC refinements across dep/auth/billing/coordinators/students/pesapal.

### Migration file history found
- deployment/phase2_billing_migration.sql:
  - Added in ea8e895
  - Removed in 4a609fc
- deployment/tiered_super_admin_access.sql:
  - No commit lineage surfaced on this branch (workspace file exists).
- deployment/dept_scoped_access.sql:
  - No commit lineage surfaced on this branch (workspace file exists).

## 2) RLS Policies Referencing is_super_admin: Dropped/Modified

Based on the current workspace SQL (tiered_super_admin_access.sql), the following are explicitly dropped/altered:

1. Policy dropped:
- super_admins_see_all_logs (audit_logs)
- Status: removed, no direct policy replacement.
- Functional replacement path: super-admin aggregate/break-glass functions.
- Classification: (a) intentionally removed as part of tiered-access rework.

2. Attendance readable in institution (attendance_records)
- Changed to institution/admin/course-unit scoped access without super_admin bypass in policy logic.
- Classification: (a) intentional.

3. API key policies replaced (api_keys)
- Org admins can view own keys
- Org admins can update own keys
- Org admins can delete own keys
- Notes in SQL indicate super_admin bypass removed from policy path.
- Classification: (a) intentional.

4. Lecturer courses policy replaced (lecturer_courses)
- Allow admins to manage lecturer_courses adjusted to institution admin path.
- Classification: (a) intentional.

Note: Because tiered_super_admin_access.sql commit history is unavailable in this branch, this policy inventory is based on the present SQL artifact rather than a full historical git old/new pair.

## 3) Frontend Gating Changes (dashboard.js and admin_screen.dart)

### dashboard.js
Observed changes include:
- Role/permission model refactor into permission flags.
- Super admin tab model changed toward tiered access (overview/break-glass style flow).
- Billing split into:
  - canViewBilling
  - canManageBilling
- Upgrade actions now guarded by canManageBilling.
- Dept-admin branch introduced with department-scoped behavior.

### Institution approval tab question
- Confirmed: pending institutions UI logic already existed before the RBAC follow-up commits and remained present.
- No direct diff evidence found showing the pending institution approval tab being removed in the reviewed RBAC commits.
- If broken in runtime, evidence suggests it was not removed in these specific RBAC diffs.

### admin_screen.dart
- Not present in repository.
- No audit diff possible in this repo for Flutter admin_screen.dart.

## 4) Backend FastAPI Role-Check Changes

### Files with role/super_admin behavior changes in today-reviewed diffs
- app/dep.py
  - Role context normalization and feature gating changes.
- app/routes/auth.py
  - Permissions response/data shape corrections and role context use.
- app/routes/admin/billing.py
  - Mutation routes restricted via central/super gate.
- app/routes/admin/sessions.py
  - Dept-admin department_id scoping behavior.
- app/routes/admin/students.py
  - Dept-admin department_id scoping and super-admin dashboard path restriction.
- app/routes/admin/coordinators.py
  - dept_admin invite requires/stores department_id.
- app/routes/webhooks/pesapal.py
  - Checkout/cart route role guard updates.

## 5) Classification Inventory

### (a) Intentionally removed/changed (expected tiered rework)
- RLS super_admin policy bypass removals listed above.
- Super-admin dashboard narrowing toward aggregate/break-glass flows.
- Department-scoped dept_admin enforcement in sessions/students/coordinators.
- Billing mutation restrictions for non-central roles.

### (b) Accidentally dropped as side effect (bug - restore)
- No clear committed diff evidence today proving an accidental RLS or route drop specifically for super_admin.

### (c) Still present but newly gated to exclude super_admin (potential bug)
- Frontend billing visibility/manage split can exclude super_admin from billing UI pathways while backend may still allow certain super-admin operations.
- This is the strongest candidate for re-gating review.

## Additional Notes
- Current repository has substantial uncommitted changes in backend and dashboard files, so part of behavior changes exist outside commit history.
- For a complete historical RLS old/new policy comparison, the missing commit lineage for tiered/dept SQL files must be recovered from the branch/repo where those files were committed.

## 6) super_admin Capability Matrix

### Platform-wide responsibilities
- See all institutions and their lifecycle state.
- Approve, suspend, or reactivate institutions.
- Inspect platform-level security posture and overview metrics.
- Use break-glass access when an institution-scoped investigation or remediation is required.
- Read audit logs across institutions, with optional filtering.
- Review analytics at the platform level.
- Manage enterprise API keys where the backend allows cross-org API operations.
- Perform billing mutations and auto-renewal operations where the backend grants super-admin parity with central admin.

### Explicitly excluded from the tiered dashboard path
- Normal student dashboard CRUD flow.
- Direct institution-scoped student deletion from the dashboard.
- Standard institution operations that should stay with dept_admin or central_admin flows, such as department management and dept-admin management.

### Current backend/frontend mismatch to keep in view
- Backend permission shaping still allows some super-admin-adjacent operations, but the frontend currently hides several of them for super_admin, especially billing, department management, dept-admin management, and API key management.
- This is a UI policy mismatch, not evidence that the backend route is missing.
- The institution approval flow is now aligned with the intended super_admin path.

## 7) Implementation Gap Check

### Implemented correctly
- Institution listing and status change are protected by super_admin checks.
- Platform overview, break-glass access, and security summary exist and are routed through super_admin-only handlers.
- Audit log retrieval supports super_admin access with optional institution filtering.
- Billing mutation endpoints accept super_admin parity with central admin.
- API key creation/listing/revocation is implemented for super_admin in the API layer.

### Implemented in backend but not exposed in the super_admin dashboard
- Billing tabs/actions are hidden for super_admin in the dashboard even though backend permission shaping allows it.
- Department management and dept-admin management are available to super_admin in backend helpers and coordinator routes, but the dashboard only renders those tabs for central_admin.
- API key management is available in backend permissions, but the dashboard only renders the API keys tab for non-super admins.

### Hard violations or missing super_admin support
- Google preflight login excludes super_admin from the Flutter allowlist, so a super_admin using that path is rejected before dashboard permissions are even evaluated.
- Attendance and AI-summary routes intentionally block super_admin, which is consistent with the current tiered model but means those functions are not part of the super_admin scope.

### Interpretation
- The codebase currently treats super_admin as a platform operator for institutions, security, analytics, audit, break-glass, and selected billing/API operations.
- The codebase does not yet consistently expose that full operator model in the dashboard UI.
- The biggest real bugs are the login allowlist exclusion and the frontend hiding of backend-permitted super_admin capabilities.
