# 📸 Smart Attendance System (AI-Powered Face Recognition)

An end-to-end AI attendance system built with **FastAPI**, **Supabase**, and a **static admin dashboard**, deployed on **DigitalOcean App Platform**.
Face recognition runs on the mobile client; the backend stores student data, images, attendance records, and provides admin APIs.

## 🚀 Features

### 🧠 AI Face Recognition
- Mobile app performs face recognition against student photos stored in Supabase.
- Embeddings generated on demand (not persisted).
- AI-powered attendance summaries and risk analysis (OpenRouter integration).

### ☁️ Cloud Storage (Supabase)
- PostgreSQL database for institutions, students, coordinators, attendance, and sessions.
- Supabase Storage for face images (`raw_faces` bucket).
- Row-level security (RLS) with service role for admin operations.

### ⚡ Backend (FastAPI)
- **Admin API**: Student/institution/coordinator management, attendance tracking, session scheduling.
- **Enterprise API**: `/v1/*` endpoints with API key authentication.
- **Payments**: Pesapal integration for billing and subscriptions.
- **Email**: Resend/SMTP for notifications and auth flows.
- **Background tasks**: APScheduler for automated syncs and cleanups.
- **Security**: Rate limiting (SlowAPI), CSP headers, Sentry error tracking.

### 🌐 Admin Dashboard (Static)
Served at `/dashboard` (`static/dashboard.html` + `dashboard.js`):
- Institution, student, and coordinator management.
- Attendance records, session scheduling, and summaries.
- Audit logs and authentication flows.

Marketing and auth pages live under `static/` (landing, login, password reset, privacy, terms).

## 📦 Deployment

### DigitalOcean App Platform

1. Create an app from this repo (Dockerfile deploy).
2. Set environment variables from `.env.example` in the DO dashboard.
3. Health check path: `/health` (see `.do/app.yaml` for reference spec).

The container runs:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

See `Dockerfile`. `Procfile` provided for alternative platforms (Heroku, Render, etc.).

## 🏗️ System Architecture

```
┌────────────────────────┐     ┌────────────────────────┐
│   Mobile app (APK)     │     │  Admin dashboard       │
│   Face recognition     │     │  /dashboard (static)   │
└───────────┬────────────┘     └───────────┬────────────┘
            │                              │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │         FastAPI              │
            │  /admin/* /v1/* /webhooks    │
            │  Pesapal, Email, Scheduler   │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │  Supabase (DB + Storage)     │
            │  PostgreSQL + Auth + Bucket  │
            └──────────────────────────────┘
```

## ⚙️ How It Works

1. **Students** — Photos and metadata are stored in Supabase (storage bucket + tables).
2. **Attendance** — The mobile app captures a face, matches against enrolled students, and calls the API to record attendance.
3. **Admins** — Sign in via Supabase Auth; the dashboard calls protected `/admin/*` and related routes on the same origin.
4. **Payments** — Pesapal integration for institutional billing and subscriptions.
5. **Notifications** — Email alerts via Resend/SMTP for password resets, auth events, and admin notifications.

## 🧪 Testing

```bash
pytest tests/
```

Security-focused regressions live in `tests/test_security_regressions.py` and `tests/test_log_login.py`.

## 🧑‍💻 Tech Stack

| Area             | Technology                          |
|:----------------:|:------------------------------------|
| Backend          | FastAPI, Python, Uvicorn            |
| Database         | Supabase (PostgreSQL + Storage)     |
| Admin UI         | Static HTML/JS (`static/`)          |
| Mobile           | Android (APK release via API)       |
| Deployment       | DigitalOcean App Platform, Docker   |
| Auth             | Supabase Auth                       |
| Payments         | Pesapal (sandbox/production)        |
| Email            | Resend / Zoho SMTP                  |
| AI               | OpenRouter (attendance summaries)   |
| Monitoring       | Sentry                              |
| Scheduling       | APScheduler                         |
| Rate Limiting    | SlowAPI                             |

## 🌍 Use Cases

- School attendance
- Employee check-in systems
- Exam hall verification
- Hostel / dormitory entry
- Visitor verification systems

## 🔑 Environment Variables

Copy `.env.example` to `.env` and configure:

- **Supabase**: `SUPABASE_URL`, `SUPABASE_KEY`, `SERVICE_KEY`
- **Payments**: `PESAPAL_ENV`, `PESAPAL_CONSUMER_KEY`, `PESAPAL_CONSUMER_SECRET`
- **Email**: `ZOHO_SMTP_USER`, `ZOHO_REFRESH_TOKEN` (or Resend)
- **AI**: `OPENROUTER_API_KEY` (optional, for attendance summaries)
- **Monitoring**: `SENTRY_DSN` (optional)
- **URLs**: `APP_URL`, `MVP_URL`, `CORS_ORIGINS`

See `.env.example` for full list with descriptions.

## 📞 Contact / Hire Me

If you need a **custom AI attendance system** or **commercial deployment**, feel free to reach out:

**Ainebyona Abubaker**  
Freelancer | AI/ML Developer  

- Fiverr: https://www.fiverr.com/s/Ege84AD
- Email: ainebyonabubaker@proton.me

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
