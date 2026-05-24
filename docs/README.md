# SmartMail AI+

> **AI-powered, event-driven customer engagement platform for e-commerce.**

SmartMail AI+ closes the gap between raw behavioural data and meaningful, personalised communication. It combines real-time event tracking, scikit-learn ML predictions, collaborative-filtering recommendations, and LLM-generated email content (Google Gemini) into a fully automated closed-loop marketing engine.

---

## Key Features

- **Real-time event ingestion** — lightweight REST endpoint + Redis Streams pipeline
- **Automated user profiling** — RFM scores, engagement index, preferred categories rebuilt every 15 min
- **ML churn & intent prediction** — Random Forest (churn) + Logistic Regression (purchase intent) retrained weekly
- **Hybrid decision engine** — rule-priority + ML-score system selects the optimal campaign type per user
- **Collaborative-filtering recommendations** — SVD/TruncatedSVD with popularity cold-start fallback
- **Gemini LLM email generation** — personalised subject + HTML body from structured prompt templates
- **End-to-end email tracking** — 1×1 pixel open tracking + click redirect UTM attribution
- **Analytics dashboard** — Next.js 14 App Router UI with KPI cards, charts, user profiles, campaign logs

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend API** | Python 3.12, FastAPI 0.115, Uvicorn |
| **Database** | PostgreSQL 16 (async via asyncpg + SQLAlchemy 2.0) |
| **Cache / Queue** | Redis 7 (Streams for event ingestion, key-value for cooldowns & recommendations) |
| **ML** | scikit-learn 1.6, pandas, NumPy, joblib |
| **Recommendation** | scikit-surprise (SVD) / sklearn TruncatedSVD fallback |
| **LLM** | Google Gemini API (`gemini-2.0-flash`) |
| **Email Delivery** | SendGrid API or SMTP (aiosmtplib) |
| **Scheduler** | APScheduler 3.10 (AsyncIO) |
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Recharts |
| **Containerisation** | Docker, Docker Compose |
| **Migrations** | Alembic |
| **Testing** | pytest + pytest-asyncio + pytest-mock (backend), Vitest + React Testing Library (frontend) |

---

## Project Structure

```
FYPJ2026/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point + lifespan
│   │   ├── config.py            # pydantic-settings config
│   │   ├── database.py          # async SQLAlchemy engine
│   │   ├── models/              # ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # FastAPI routers (one per domain)
│   │   ├── services/            # Business logic layer
│   │   ├── workers/             # Redis event consumer + APScheduler
│   │   └── prompts/             # LLM prompt templates (.txt)
│   ├── ml/                      # Training scripts + feature pipeline
│   ├── alembic/                 # Database migrations
│   └── data/seed.py             # Idempotent seed data
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # Reusable React components
│   └── lib/api.ts               # Typed API client
├── docker-compose.yml
└── .env.example
```

---

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ and npm
- Python 3.12 and pip

### 1. Clone and Configure

```bash
git clone <repo-url>
cd FYPJ2026
cp .env.example .env
# Edit .env — fill in GEMINI_API_KEY, API_SECRET_KEY, email credentials
```

### 2. Start Infrastructure (PostgreSQL + Redis + MailHog)

```bash
docker compose up postgres redis mailhog -d
```

### 3. Run the Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
alembic upgrade head          # Run migrations
python data/seed.py           # Seed demo data
$env:PYTHONPATH="."; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Access

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:3000 |
| Backend API Docs | http://localhost:8000/docs |
| MailHog Web UI | http://localhost:8025 |

---

## Architecture Overview

```
Browser → Next.js Frontend → FastAPI Backend → PostgreSQL
                                    ↓
                              Redis Streams ← Event Tracking
                                    ↓
                           Event Worker (async)
                                    ↓
                           APScheduler Jobs
                          (analytics / ML / campaigns)
                                    ↓
                           Gemini API → Email → SendGrid/SMTP
```

See [2-architecture.md](./2-architecture.md) for the full Mermaid diagram and component descriptions.

---

## Documentation Index

| File | Contents |
|------|----------|
| [1-overview.md](./1-overview.md) | Problem statement, goals, target users |
| [2-architecture.md](./2-architecture.md) | System components and interaction diagram |
| [3-features.md](./3-features.md) | Complete feature catalogue |
| [4-api-spec.md](./4-api-spec.md) | All API endpoints with request/response |
| [5-database.md](./5-database.md) | Schema, relationships, field descriptions |
| [6-workflows.md](./6-workflows.md) | Key system flows (event → email, ML pipeline) |
| [7-deployment.md](./7-deployment.md) | Local, Docker, and cloud deployment |
| [8-decisions.md](./8-decisions.md) | Architecture Decision Records (ADRs) |
