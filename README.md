# Pearson Spectre — Fully Integrated AI Contract Compliance Platform

## Architecture

```
pearson-spectre-frontend/   ← Next.js 14 (App Router)
anvil-backend/              ← FastAPI + LangGraph (6-agent pipeline)
```

## Quick Start

### 1. Start the Backend

```bash
cd anvil-backend

# Install dependencies
pip install -r requirements.txt

# Copy and configure env
cp .env .env.local   # already configured for local dev

# Run the server (auto-seeds demo users on first launch)
python main.py
# OR
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

### 2. Start the Frontend

```bash
cd pearson-spectre-frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at: http://localhost:3000

---

## Login Credentials

| Role     | Email                   | Password      |
|----------|------------------------|---------------|
| Admin    | admin@spectre.ai       | admin123      |
| Legal    | legal@spectre.ai       | legal123      |
| Security | security@spectre.ai    | security123   |

> Demo users are auto-seeded on first backend launch. No manual seeding needed.

---

## What's Integrated

### Authentication
- JWT login/logout with token stored in localStorage
- AuthGuard protects all routes — redirects to `/login` if not authenticated
- User name + role shown in top-bar with logout button
- 24-hour token expiry

### Dashboard (`/`)
- **Stats cards** — live from `/api/analytics/dashboard`
- **Recent Workflows** — live from `/api/workflows/` + `/api/contracts/`
- **Live Activity** — pulls from `/api/analytics/activity-feed` on load, then connects to SSE at `/api/events/stream` for real-time updates

### Contract Vault (`/vault`)
- Lists all contracts from `/api/contracts/`
- Shows finding count per contract (from `/api/contracts/{id}/findings`)
- Delete button (admin only)
- "View Analysis →" links to Risk page filtered by contract

### Upload (`/upload`)
- Drag-and-drop PDF upload to `/api/contracts/upload`
- Triggers the 6-agent LangGraph pipeline automatically
- Shows recent uploads live from API

### Risk Analysis (`/risk`)
- Contract selector populated from API
- Findings table from `/api/contracts/{id}/findings`
- Full clause redline panel with original text, proposed rewrite, regulation cite
- Supports `?contract=<id>` and `?run=<id>` URL params

### Workflows (`/workflows`)
- All runs from `/api/workflows/`
- Shows agent tasks, status, confidence, runtime
- Links to findings for each run

### Traces (`/traces`)
- All workflow runs with agent task breakdown
- Aggregate stats (total runs, success rate, avg runtime)
- Per-agent status color coding

### Regulation Feed (`/feed`)
- Regulations from `/api/regulations/`
- Falls back to static content if DB is empty

---

## The 6-Agent Pipeline

When a contract is uploaded, this LangGraph pipeline fires automatically:

1. **Ingest** — reads and validates the PDF blob
2. **Extraction** — splits into clauses, filters noise
3. **Research** — fetches active regulations from DB
4. **Classifier** — Gemini LLM classifies each clause for violations
5. **Redline** — generates rewrite suggestions for flagged clauses
6. **Reporter** — saves findings to DB, fires Slack/GitHub notifications

All agents emit SSE events visible in the Live Activity panel in real-time.

---

## Environment Configuration

### Backend (`anvil-backend/.env`)
```
GEMINI_API_KEY=your_key_here          # Required for AI classification
SECRET_KEY=your_secret_here           # JWT signing key
GITHUB_TOKEN=...                      # Optional: PR creation
SLACK_WEBHOOK_URL=...                 # Optional: Slack notifications
```

### Frontend (`pearson-spectre-frontend/.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Production Deployment

For production, update:
- `NEXT_PUBLIC_API_URL` to your backend's public URL
- `SECRET_KEY` to a long random string
- CORS origins in `main.py` to your frontend domain
