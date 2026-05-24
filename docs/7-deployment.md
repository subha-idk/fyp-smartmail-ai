# 7. Deployment

## Local Development (without Docker)

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.12+ |
| Node.js | 18+ |
| PostgreSQL | 16 |
| Redis | 7 |

### Step 1 — Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `GEMINI_API_KEY` — Google AI Studio API key
- `API_SECRET_KEY` — any random string (used for X-API-Key auth)
- Email credentials (`SENDGRID_API_KEY` or `SMTP_*` fields)

### Step 2 — Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# (Optional) Seed demo data
$env:PYTHONPATH="."; python data/seed.py

# Start the API server
$env:PYTHONPATH="."; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3 — Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Step 4 — Verify

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Swagger | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

---

## Docker Compose (Recommended)

Runs all services — PostgreSQL, Redis, Backend, Frontend, and MailHog — in isolated containers.

### Prerequisites
- Docker Desktop (or Docker Engine + Compose plugin)

### Step 1 — Configure

```bash
cp .env.example .env
# Fill in GEMINI_API_KEY, API_SECRET_KEY, and other required values
```

### Step 2 — Start All Services

```bash
docker compose up -d
```

This starts:

| Service | Port(s) | Image |
|---------|---------|-------|
| `postgres` | 5433:5432 | postgres:16-alpine |
| `redis` | 6379:6379 | redis:7-alpine |
| `backend` | 8000:8000 | Custom (./backend/Dockerfile) |
| `frontend` | 3000:3000 | Custom (./frontend/Dockerfile) |
| `mailhog` | 1025 (SMTP), 8025 (UI) | mailhog/mailhog |

### Step 3 — Run Migrations

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python data/seed.py
```

### Step 4 — Access

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:3000 |
| Backend API Docs | http://localhost:8000/docs |
| MailHog (dev email inbox) | http://localhost:8025 |

### Useful Commands

```bash
# View logs
docker compose logs -f backend

# Rebuild backend after code changes
docker compose up -d --build backend

# Scale backend replicas
docker compose up -d --scale backend=3

# Stop all
docker compose down

# Destroy volumes (wipe DB)
docker compose down -v
```

---

## Environment Variables Reference

All settings are loaded via `pydantic-settings` from `.env`. Never hardcode values.

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5432/smartmail` | PostgreSQL async connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |

### Authentication

| Variable | Description |
|----------|-------------|
| `API_SECRET_KEY` | Shared secret for `X-API-Key` header auth |

### Gemini API

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Google AI Studio key |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Model to use |
| `LLM_MAX_TOKENS` | `1000` | Max tokens per generation |
| `LLM_MONTHLY_TOKEN_BUDGET` | `5000000` | Monthly budget cap |

### Email Delivery

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_PROVIDER` | `sendgrid` | `sendgrid` or `smtp` |
| `SENDGRID_API_KEY` | — | SendGrid API key |
| `SMTP_HOST` | `localhost` | SMTP server hostname |
| `SMTP_PORT` | `1025` | SMTP port |
| `SMTP_USERNAME` | — | SMTP credential |
| `SMTP_PASSWORD` | — | SMTP credential |
| `SMTP_USE_TLS` | `true` | Enable STARTTLS |
| `EMAIL_FROM_ADDRESS` | — | Sender email address |
| `EMAIL_FROM_NAME` | `SmartMail AI+` | Sender display name |

### ML Thresholds (all tunable)

| Variable | Default | Description |
|----------|---------|-------------|
| `CHURN_RISK_THRESHOLD` | `0.7` | Minimum churn score to trigger retention email |
| `PURCHASE_PROB_THRESHOLD` | `0.6` | Minimum intent score to trigger recommendation email |
| `TOP_SPENDER_THRESHOLD` | `500.0` | Spend threshold for upsell campaign |
| `CART_ABANDON_HOURS` | `24` | Hours before abandoned cart email fires |
| `EMAIL_COOLDOWN_HOURS` | `24` | Minimum hours between emails per user |

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://localhost:8000` | Backend base URL (used in tracking links) |
| `FRONTEND_URL` | `http://localhost:3000` | Frontend base URL (CORS + redirect fallback) |
| `DEBUG` | `true` | Enable debug mode |

### Frontend (exposed to browser)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend URL accessible from the browser |
| `NEXT_PUBLIC_API_KEY` | API key sent in `X-API-Key` header from frontend |

---

## ML Model Setup

Before ML predictions are available, trained models must exist in `backend/ml/models/`.

### Train Models (first time)

```bash
cd backend

# 1. Build feature CSVs from current data
$env:PYTHONPATH="."; python ml/feature_pipeline.py

# 2. Train churn model
$env:PYTHONPATH="."; python ml/train_churn.py

# 3. Train intent model
$env:PYTHONPATH="."; python ml/train_intent.py
```

Saved files: `ml/models/churn_v1.pkl`, `ml/models/intent_v1.pkl`

> **Note:** Models require at minimum ~500 user-event records for meaningful predictions. With seed data, accuracy on dummy data targets F1 ≥ 0.65.

### Automatic Weekly Retraining

APScheduler runs `weekly_retrain_job()` every Sunday at 02:00 UTC — this rebuilds features from current data, retrains both models, and updates the Redis version pointer so inference workers pick up the new models without restart.

---

## Production Deployment Checklist

- [ ] Set `DEBUG=false`
- [ ] Use a strong random `API_SECRET_KEY` (min 32 characters)
- [ ] Use a managed PostgreSQL instance (e.g. AWS RDS, Supabase, Neon)
- [ ] Use a managed Redis instance (e.g. AWS ElastiCache, Upstash)
- [ ] Configure `EMAIL_PROVIDER=sendgrid` with a real SendGrid API key
- [ ] Set `GEMINI_API_KEY` and configure monthly budget
- [ ] Set `BACKEND_URL` and `FRONTEND_URL` to production domains
- [ ] Configure SMTP TLS/SSL appropriately
- [ ] Run `alembic upgrade head` before deploying a new version
- [ ] Mount `backend/ml/models/` as a persistent volume to survive container restarts
- [ ] Set up health check probes on `/health` (backend) and `/` (frontend)
- [ ] Add structured logging / APM (e.g. Sentry, Datadog) for observability

---

## Dockerfile Reference

### Backend (`backend/Dockerfile`)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (`frontend/Dockerfile`)

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev"]
```
