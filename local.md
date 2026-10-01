# Local Development

## Python environment

The backend uses the existing Python 3.14 environment:

```text
/home/abubaker/venvs/env_3.14
```

The repository-local `.venv` was empty and has been removed. Do not recreate it unless a separate project environment is needed.

## Run with systemd

The backend runs as a user-level systemd service:

```text
~/.config/systemd/user/faceattend-backend.service
```

The service uses Uvicorn on port `8080` and starts automatically with the user session.

```bash
systemctl --user start faceattend-backend
systemctl --user stop faceattend-backend
systemctl --user restart faceattend-backend
systemctl --user status faceattend-backend
journalctl --user -u faceattend-backend -f
```

Open the local application at:

- http://localhost:8080
- http://localhost:8080/dashboard
- http://localhost:8080/health

The health endpoint should return:

```json
{"status":"ok"}
```

## Manual development run

To run outside systemd with the development reloader:

```bash
VENV=/home/abubaker/venvs/env_3.14 make run
```

Stop the manual server before starting the systemd service if both use port `8080`.

## Environment and Supabase

There is no local `.env` file. Only `.env.example` is present, and these backend variables are currently unset:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SERVICE_KEY`

The backend still starts without them. Public pages and `/health` work, but server-side authentication, database, storage, billing, email, and other Supabase-backed operations require the appropriate environment variables.

The browser dashboard includes the public Supabase URL and publishable key in its frontend JavaScript, so it can authenticate against the hosted Supabase project even without a local `.env`. The dashboard also currently uses the deployed API base for many requests, so local UI access does not guarantee that data operations are isolated from production.

Never place `SERVICE_KEY` or another server secret in frontend JavaScript.

## Git branches

The active branch is `development`, which tracks `origin/development`. The Copilot branch was already fully merged and was deleted from GitHub. The remaining remote branches are:

- `development`
- `admin-panel`

Local code changes do not affect deployment until they are committed, pushed, and processed by the deployment workflow. Requests from the local dashboard can still affect hosted services when its configured API or Supabase endpoints are used.
