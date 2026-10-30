# CityWatch AI cloud deployment

This repository is prepared for Vercel (React/Vite), Render (FastAPI), and Supabase (PostgreSQL plus private evidence storage). The application is not deployed by these repository changes; there are no production project URLs or credentials in this checkout.

## 1. Prepare Supabase

1. Create a Supabase project and save the database password. Do not commit it.
2. In **SQL Editor**, run `supabase/migrations/202610300001_citywatch_cloud.sql`. It creates the `citywatch` schema and required tables/indexes if absent, adds compatible columns without dropping records, adds forward-enforced foreign keys as `NOT VALID` so pre-existing orphan rows are preserved, and creates a private `evidence` bucket. It is safe to re-run against an existing CityWatch schema.
3. Keep the bucket private. The backend uses the service-role key for storage operations and sends evidence through authenticated API routes after complaint access checks. Never put the service-role key in Vercel or a `VITE_*` variable.
4. For a new deployment, use the Supabase **Transaction pooler** connection string for Render (typically port `6543`) and append `sslmode=require`. Preserve the user/project portion Supabase supplies; URL-encode special characters in the password. The backend sets a `citywatch,public` search path, a connection timeout, SSL, and keepalives.
5. Existing PostgreSQL records are preserved by the `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` migration. Before applying to an existing project, take a Supabase backup or restore point and verify the target project/ref.

### Move existing local evidence (if present)

The deployment cannot carry evidence from a laptop's disk automatically. Copy the existing `backend/uploads` directory into this checkout first, set the backend environment variables locally, then run from `backend`:

```powershell
python migrate_evidence_to_storage.py
python migrate_evidence_to_storage.py --apply
```

The first command is a dry run. `--apply` uploads evidence and changes only database object paths; local originals are retained. Review the summary and missing files before deploying. This utility migrates evidence attached to existing PostgreSQL complaints. The older optional SQLite importer only copies basic complaint rows; it does **not** migrate users, assignments, departments, history, or evidence. Do not enable `CITYWATCH_IMPORT_LEGACY_SQLITE` as a substitute for a planned full legacy-data migration.

## 2. Deploy the FastAPI backend to Render

Create a new **Blueprint** from this repository using `render.yaml`, or configure a Web Service manually:

- Root directory: `backend`
- Runtime: Python 3.11.11
- Build command: `pip install --upgrade pip && pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/api/health`
- Instance: Standard or larger. TensorFlow and OpenCV need more memory than the free tier provides reliably; use at least 2 GB RAM and monitor memory during model inference.

Set these Render environment variables:

| Variable | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `CITYWATCH_AUTO_MIGRATE` | `false` (schema is applied explicitly in Supabase first) |
| `CITYWATCH_SEED_DEMO_ACCOUNTS` | `false` |
| `DATABASE_URL` | Supabase transaction-pooler URI with `sslmode=require` |
| `DATABASE_POOL_MAX` | `8` (per Render instance; lower this if Supabase pool limits require it) |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase server-side service-role key (Render secret only) |
| `SUPABASE_STORAGE_BUCKET` | `evidence` |
| `SECRET_KEY` | Random secret, at least 32 characters; Render Blueprint can generate it |
| `CORS_ORIGINS` | Exact Vercel origin(s), comma separated, e.g. `https://citywatch-ai.vercel.app` |
| `CITYWATCH_ROAD_MODEL_PATH` | `models/road_damage_5class_model.keras` |

`backend/.env.example` also includes split `SUPABASE_DB_*` settings for local development. The `DATABASE_URL` setting takes precedence in Render. The Keras model is tracked at `backend/models/road_damage_5class_model.keras`; startup loads it lazily once per process. Video frame classification is run in FastAPI's worker pool, with upload size/frame limits already applied. Keep at least one Render instance warm if the cold-start delay is unsuitable.

After the first deploy, copy the Render service URL (for example `https://citywatch-ai-api.onrender.com`). Confirm `https://<render-host>/api/health` reports healthy before setting up Vercel.

## 3. Deploy the Vite frontend to Vercel

Import the GitHub repository into Vercel and set:

- Root directory: `frontend`
- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`
- Install command: `npm install` (or `npm ci`)
- Node.js: 22.12 or newer (also declared in `package.json`)
- Environment variable: `VITE_API_BASE_URL=https://<render-host>/api`

The Vercel rewrite in `frontend/vercel.json` sends nested client routes to the SPA entry point. After Vercel assigns a domain, add that exact origin to Render's `CORS_ORIGINS`, then redeploy the API. If using a custom domain, include it too. No Vite variable should contain a database or service-role secret.

## 4. Local development

Copy `backend/.env.example` to `backend/.env`, set a Supabase development project (or use a separate PostgreSQL dev database), and keep `CITYWATCH_AUTO_MIGRATE=true`. Set `SECRET_KEY` or let development create a local secret. Demo accounts seed in development by default. Copy `frontend/.env.example` to `frontend/.env.local`; its default points to `http://localhost:8000/api`.

Run the backend from `backend` with `uvicorn main:app --reload --port 8000`; run the frontend from `frontend` with `npm run dev`.

## 5. Verification

Before inviting users, verify each item against the deployed URLs:

- `GET /api/health` returns 200 and `"database": "ready"`.
- Vercel root and a nested route (for example `/details/<id>`) load directly and after refresh.
- Citizen signup/login, logout, and role restrictions work against the Render API.
- The citizen dashboard shows points only for verified reports (20 each) and support reports (5 each); pending reports do not earn points.
- Submit an image complaint; confirm a PostgreSQL complaint/evidence row, private Storage object, duplicate warning behavior, and evidence preview in the detail route.
- Confirm a direct API submission with a match receives `duplicate_confirmation_required`, while the citizen's “Submit as New Complaint” confirmation lets the original evidence be saved.
- Submit a video at the size limit and confirm authorized playback; verify a different citizen cannot retrieve it.
- Confirm the road model returns an AI analysis for supported categories and gracefully leaves unsupported cases for review.
- Verify department review, officer assignment, duplicate-linked assignment protection, dashboard counts, progress updates, and citizen tracking.
- Confirm CORS rejects an unrelated browser origin and permits the Vercel origin.
- Watch Render memory, request latency, and logs while processing video. The standard Render web service is not a background job queue; very long video analysis still occupies a request worker.

Production endpoints cannot be exercised until the Supabase project, Render service, Vercel project, and their secrets/domains have been created. Do not treat a local build or health response as proof of the complete cloud flow.

## 6. GitHub push

From the repository root, review the diff and make sure `.env` files and local uploads are not staged. Then:

```powershell
git add DEPLOYMENT.md render.yaml frontend/vercel.json frontend/package.json frontend/package-lock.json frontend/.env.example frontend/src backend/.env.example backend/database.py backend/main.py backend/routes backend/services backend/migrate_evidence_to_storage.py supabase/migrations/202610300001_citywatch_cloud.sql
git diff --cached --check
git commit -m "Prepare CityWatch AI for cloud deployment"
git push origin main
```

Adjust the branch name if the repository uses a different deployment branch. Review and commit pre-existing workspace changes separately if they are not part of this deployment work.

## Known limits

- The application has no real production URLs or Supabase credentials in this change, so a cloud deployment and end-to-end production verification are still pending.
- No full migration from an unspecified legacy MySQL instance is included. Existing Supabase PostgreSQL data is preserved in place; local SQLite import remains an explicitly incomplete complaint-only utility.
- Uploads are private and routed through FastAPI, so large videos consume backend bandwidth and RAM. Render request timeouts and single-instance memory should be observed; a durable background queue would be a separate architecture change.
- The application keeps a small PostgreSQL client pool per Render instance and relies on Supabase's transaction pooler for server-side connection management. Review pooler limits and lower `DATABASE_POOL_MAX` when scaling Render instances.
