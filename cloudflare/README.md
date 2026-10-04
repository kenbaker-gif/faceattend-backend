# Cloudflare Container deployment

This branch contains an experimental Cloudflare Workers front end for the existing FastAPI Docker image.

## Architecture

- `cloudflare/worker.ts` routes requests to one named Cloudflare Container.
- `wrangler.jsonc` builds the repository `Dockerfile` as the container image.
- FastAPI, Supabase, static assets, and Uvicorn remain inside the container.

## Prerequisites

- Cloudflare Workers Paid plan with Containers enabled.
- Docker running locally for the first `wrangler deploy`.
- Wrangler and the Cloudflare Containers package installed:

```bash
npm install -D wrangler typescript @cloudflare/containers
```

Set the backend secrets as Cloudflare Container environment variables before deploying. Do not commit them:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SERVICE_KEY`
- `MVP_URL`
- `APP_URL`
- `CORS_ORIGINS`
- payment, email, AI, and monitoring secrets required by the enabled routes

## Local validation

From the repository root:

```bash
npx wrangler deploy --dry-run
```

## Deployment

```bash
npx wrangler deploy
```

The container is intentionally limited to one instance while this branch is evaluated. The existing APScheduler jobs should be moved to Cloudflare Cron Triggers or Workflows before increasing `max_instances` or using this path for production.
