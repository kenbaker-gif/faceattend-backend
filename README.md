# 📸 Smart Attendance System (AI-Powered Face Recognition)

An end-to-end AI attendance system built with **FastAPI**, **Supabase**, and a **static admin dashboard**, deployed on **DigitalOcean App Platform**.
Face recognition runs on the mobile client; the backend stores student data, images, attendance records, and admin APIs.

## 🚀 Features

### 🧠 AI Face Recognition

- Mobile app uses face recognition against student photos in Supabase.
- Embeddings are generated on demand (not stored in the DB).

### ☁️ Cloud Storage (Supabase)

- Student profiles, institutions, and face images.
- Attendance records and audit logs.

### ⚡ Backend (FastAPI)

- REST API for uploads, attendance, student management, billing, and enterprise `/v1` access.
- Rate limiting, security headers, and Sentry integration.

### 🌐 Admin dashboard (static)

Served by FastAPI at `/dashboard` (`static/dashboard.html` + `dashboard.js`):

- Institution and student management
- Attendance records and summaries
- Audit logs and admin auth flows

Marketing and auth pages live under `static/` (login, password reset, privacy, terms).

## 📦 Deployment

Production runs a single process:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### DigitalOcean App Platform

1. Create an app from this repo (Dockerfile deploy).
2. Set environment variables from `.env.example` in the DO dashboard.
3. Health check path: `/health` (see `.do/app.yaml` for a reference spec).

The container runs:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

See `Dockerfile`. `Procfile` is optional for other hosts.

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
            │  (DigitalOcean / Docker)     │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │  Supabase (DB + Storage)     │
            └──────────────────────────────┘
```

## ⚙️ How It Works

1. **Students** — Photos and metadata are stored in Supabase (storage bucket + tables).
2. **Attendance** — The mobile app captures a face, matches against enrolled students, and calls the API to record attendance.
3. **Admins** — Sign in via Supabase Auth; the dashboard calls protected `/admin/*` and related routes on the same origin.

## 🧪 Testing

```bash
pytest tests/
```

Security-focused regressions live in `tests/test_security_regressions.py` and `tests/test_log_login.py`.

## 🧑‍💻 Tech Stack

| Area        | Technology                          |
|:-----------:|:------------------------------------|
| Backend     | FastAPI, Python                     |
| Database    | Supabase (PostgreSQL + Storage)     |
| Admin UI    | Static HTML/JS (`static/`)          |
| Mobile      | Android (APK release via API)       |
| Deployment  | DigitalOcean App Platform, Docker   |
| Auth        | Supabase Auth                       |

## 🌍 Use Cases

- School attendance
- Employee check-in systems
- Exam hall verification
- Hostel / dormitory entry
- Visitor verification systems

## 📞 Contact / Hire Me

If you need a **custom AI attendance system** or **commercial deployment**, feel free to reach out:

**Ainebyona Abubaker**  
Freelancer | AI/ML Developer  

- Fiverr: https://www.fiverr.com/s/Ege84AD
- Email: ainebyonabubaker@proton.me

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
