# Worker PWA

Standalone worker-facing Progressive Web App for WhatsApp handoff links.

## Why standalone?

This app is intentionally separate from the admin frontend so worker UX and release lifecycle can evolve independently without risking admin regressions.

## Routes

- `/share/worker/:token` - Worker profile via secure share token

## Local development

### One-command startup (recommended)

- From repo root run:
   - `docker-compose up --build`
- Services started:
   - Admin frontend: `http://localhost:3000`
   - Worker PWA: `http://localhost:4173`
   - Backend API: `http://localhost:8000`

### Run worker PWA only

1. Start backend and admin stack:
   - `docker-compose up`
2. Run worker PWA separately:
   - `cd worker-pwa`
   - `cp .env.example .env`
   - `npm install`
   - `npm run dev`
3. Open:
   - `http://localhost:4173/share/worker/<token>`

## Production deployment (Vercel)

- Deploy `worker-pwa` as a separate Vercel project.
- Keep this app on a worker-specific domain (recommended):
  - `worker.<your-domain>` or `<project>-worker.vercel.app`
- Set backend env vars on Render:
  - `WORKER_PWA_URL=https://<worker-pwa-domain>`
  - `WORKER_PWA_LOCAL_URL=http://localhost:4173`

## Notes

- App is mobile-first and installable via Web App Manifest + service worker.
- Share token APIs are served by backend under `/api/v1/share-tokens/*`.
- Worker updates from PWA write directly to the same `workers` table used by backend/admin.
