#!/bin/sh
# Run inside Docker build context or after `docker build` to verify app before deploy.
set -e

export SUPABASE_URL="${SUPABASE_URL:-https://example.supabase.co}"
export SUPABASE_KEY="${SUPABASE_KEY:-test-anon-key}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-test-anon-key}"
export SERVICE_KEY="${SERVICE_KEY:-test-service-role-key}"

echo "==> pytest"
python -m pytest tests/ -v --tb=short

echo "==> import app.main and list routes"
python - <<'PY'
from app.main import app

paths = sorted({getattr(r, "path", None) for r in app.routes if getattr(r, "path", None)})
required = [
    "/",
    "/health",
    "/dashboard",
    "/upload-student-face",
    "/students",
    "/admin/attendance-records",
    "/invite-coordinator",
    "/register-institution",
    "/plans",
    "/v1",
]
missing = [p for p in required if p not in paths and not any(x.startswith(p) for x in paths)]
if missing:
    raise SystemExit(f"Missing expected routes: {missing}")
print(f"OK: {len(paths)} routes registered")
for p in paths:
    if p in required or p.startswith("/admin") or p.startswith("/v1") or p.startswith("/api/cart"):
        print(f"  {p}")
PY

echo "==> smoke: TestClient /health and /"
python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.get("/health")
assert r.status_code == 200 and r.json() == {"status": "ok"}, r.text
r = client.get("/")
assert r.status_code == 200, r.text
r = client.get("/dashboard")
assert r.status_code == 200, r.text
print("OK: /health, /, /dashboard return 200")
PY

echo "==> All checks passed"
