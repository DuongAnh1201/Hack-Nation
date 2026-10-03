# Physics Study 3D

Study platform for visualizing 3D physics problems, with AI agents (Databricks OmniAgent) as a tutor.

## Structure

```
.
├── frontend/                 Vite + React + TypeScript + Three.js (react-three-fiber) → Vercel
│   └── src/
│       ├── scenes/           3D physics scenes (one per problem type)
│       ├── components/       UI: controls, panels, tutor chat
│       ├── lib/              Pure physics/math functions (unit-tested)
│       └── api/              Backend client
├── backend/                  FastAPI (Python 3.12) → Render
│   ├── app/
│   │   ├── main.py           App entry, CORS, /health
│   │   ├── api/              HTTP routes
│   │   ├── agents/           OmniAgent config + orchestration
│   │   └── core/             Settings, rate limiting, shared utilities
│   └── tests/
├── .github/workflows/ci-cd.yml
└── render.yaml               Render Blueprint for the backend
```

## Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload            # http://localhost:8000/health

# Frontend (second terminal)
cd frontend
npm install
cp .env.example .env
npm run dev                               # http://localhost:5173 (proxies /api to :8000)
```

## CI/CD

| Event | What runs |
|---|---|
| Pull request | Frontend: typecheck, test, build. Backend: ruff lint + format check, pytest. Then a Vercel **preview** deploy. |
| Push to `main` | Same checks, then Render deploy → Vercel production deploy → health-check smoke test. |

Nothing deploys unless every check passes.

## One-time deployment setup

**1. Render (backend)**
1. Render dashboard → New → Blueprint → select this repo (uses `render.yaml`).
2. Fill in the env vars it prompts for (`FRONTEND_ORIGINS` = your Vercel URL, API keys).
3. Service → Settings → Deploy Hook → copy the URL.

**2. Vercel (frontend)**
1. Import the repo in Vercel, set **Root Directory = `frontend`**.
2. Disable Vercel's own Git auto-deploys (Settings → Git → Ignored Build Step: `exit 0`) so GitHub Actions controls deploys.
3. Project env var: `VITE_API_URL` = your Render URL.
4. Create a token: Account Settings → Tokens.
5. Get org/project IDs: run `npx vercel link` locally, then read `.vercel/project.json`.

**3. GitHub (Settings → Secrets and variables → Actions)**

| Name | Type | Value |
|---|---|---|
| `VERCEL_TOKEN` | Secret | Vercel token |
| `VERCEL_ORG_ID` | Secret | from `.vercel/project.json` |
| `VERCEL_PROJECT_ID` | Secret | from `.vercel/project.json` |
| `RENDER_DEPLOY_HOOK_URL` | Secret | Render deploy hook |
| `BACKEND_URL` | Variable | e.g. `https://physics-study-api.onrender.com` |

Optional: Settings → Branches → protect `main`, require the `frontend` and `backend` checks.

## Cost notes

- Render free: sleeps after 15 min idle (~1 min cold start). Switch `plan` to `starter` ($7/mo) in `render.yaml` before demo day.
- Set hard spending caps on every LLM API key.
- Bright Data (`BRIGHTDATA_API_TOKEN`) is optional, for agent web search/scraping only.
