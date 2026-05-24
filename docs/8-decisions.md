# 8. Architecture Decision Records (ADR)

Architecture Decision Records document the key technical choices made during the design and development of SmartMail AI+, including the rationale and trade-offs considered.

---

## ADR-001: Redis Streams for Event Ingestion

**Status:** Accepted

### Decision
Use Redis Streams (`XADD` / `XREADGROUP`) as the event queue between the HTTP tracking endpoint and the PostgreSQL writer, rather than writing events directly to the database on each request.

### Rationale
- **Decoupling** — the tracking endpoint returns `202 Accepted` in < 100 ms regardless of database load, preventing back-pressure from slowing the storefront.
- **Durability** — Redis Streams persist messages even if the consumer crashes; messages are redelivered on restart via the consumer group.
- **Batching** — the event worker batches up to 50 messages per database transaction, significantly reducing connection and write overhead at scale.
- **Dead-lettering** — failed messages are automatically moved to `events:failed` for inspection without data loss.

### Alternatives Considered
- **Direct PostgreSQL write** — simpler but tight coupling; high-volume events could cause database contention and increase API latency.
- **Celery + RabbitMQ** — more powerful but adds operational complexity (broker, workers, flower) not justified at v1 scale.

### Trade-offs
- Introduces Redis as a required infrastructure dependency.
- Small eventual-consistency window between event firing and PostgreSQL persistence (typically < 1 s).

---

## ADR-002: Async SQLAlchemy with asyncpg

**Status:** Accepted

### Decision
Use SQLAlchemy 2.0 async with the `asyncpg` driver for all database operations.

### Rationale
- FastAPI is built on `asyncio` — using synchronous SQLAlchemy would block the event loop and negate concurrency benefits.
- `asyncpg` is the fastest Python PostgreSQL driver by throughput benchmarks.
- SQLAlchemy 2.0 provides full async ORM support with type-annotated mapped columns.

### Alternatives Considered
- **`psycopg2` (sync)** — incompatible with async FastAPI without `asyncio.to_thread` wrapping.
- **`databases` library** — lighter, but less mature ORM and no Alembic integration.
- **Raw asyncpg** — maximum performance, but no ORM abstraction or migration tooling.

### Trade-offs
- Requires all service methods to be `async def` throughout.
- Slightly more complex session management (`async_session_factory` context managers).

---

## ADR-003: APScheduler Instead of a Dedicated Task Queue

**Status:** Accepted

### Decision
Run background periodic jobs (analytics refresh, ML inference, campaign trigger, weekly retrain) using APScheduler in `AsyncIOScheduler` mode within the FastAPI process, rather than a separate Celery/RQ worker fleet.

### Rationale
- **Simplicity** — no separate worker processes, broker, or queue infrastructure needed for v1.
- **Co-location** — scheduled jobs share the same SQLAlchemy session factory and Redis connection as the API, avoiding connection duplication.
- **Sufficient for scale** — 10,000 events/day with 500 users processes comfortably within single-process async loops.

### Alternatives Considered
- **Celery + Redis broker** — industry-standard for distributed task queues; better suited when tasks need horizontal scaling across nodes.
- **ARQ (async task queue)** — lighter than Celery, but still requires a separate worker process.

### Trade-offs
- Jobs run in the same process as the API — a long-running retrain job could increase event loop latency.
- Cannot distribute jobs across multiple servers in v1 (mitigated by the 50-user cap on the campaign trigger job).

### Upgrade Path
Replace APScheduler with Celery + Redis broker when traffic exceeds single-node capacity.

---

## ADR-004: Hybrid Rule + ML Decision Engine

**Status:** Accepted

### Decision
The email campaign type selection uses a strict **priority-ordered rule list** that evaluates ML scores (churn risk, purchase probability) as conditions, rather than a pure ML classifier or a pure rule engine.

### Rationale
- **Explainability** — marketers can understand and audit why a specific email was sent to a specific user.
- **Business control** — thresholds (`CHURN_RISK_THRESHOLD`, etc.) are configurable env vars, allowing business teams to tune behaviour without code changes.
- **ML as signal, rules as guardrails** — ML scores inform decisions but are bounded by the business logic (e.g. cooldowns always override ML scores).
- **Reliability** — if the ML model is unavailable or returns `null`, the decision engine degrades gracefully to rule-based fallbacks.

### Alternatives Considered
- **Pure ML classifier** — predicts email type directly; higher accuracy but no explainability or easy business-rule overrides.
- **Pure rule engine** — no ML; easier to reason about but misses nuanced behavioural signals.

### Trade-offs
- The priority order is static code — changing it requires a code deploy.
- Rules may conflict with ML signals (e.g. a user is a top spender but also at high churn risk; retention wins over upsell).

---

## ADR-005: Google Gemini for Email Generation

**Status:** Accepted

### Decision
Use the Google Gemini API (`gemini-2.0-flash`) to generate personalised email subject lines and HTML bodies, rather than static templates or a self-hosted LLM.

### Rationale
- **Quality** — Gemini produces natural, brand-appropriate copy that adapts to user context (name, category, scores, product).
- **Structured output** — instructing the model to return JSON (`subject`, `html_body`, `plain_body`) enables reliable programmatic parsing.
- **Speed** — `gemini-2.0-flash` is optimised for low-latency inference, keeping email dispatch under the 5-minute SLA.
- **Cost control** — `LLM_MONTHLY_TOKEN_BUDGET` (5 M tokens default) caps spend; `tokens_used` is logged per email for monitoring.

### Alternatives Considered
- **Static templates** — deterministic and zero-cost; already implemented as the fallback path.
- **OpenAI GPT-4o** — comparable quality; Gemini chosen for Google Cloud ecosystem alignment.
- **Self-hosted Llama** — no API cost but requires GPU infrastructure and fine-tuning.

### Trade-offs
- External API dependency — network failures or API quota exhaustion can delay email dispatch.
- **Mitigation:** Two-level fallback — (1) raw template rendering if Gemini fails; (2) hardcoded generic string if template rendering also fails.

---

## ADR-006: Collaborative Filtering for Recommendations

**Status:** Accepted

### Decision
Use a matrix-factorisation approach (SVD via scikit-surprise, or TruncatedSVD via sklearn as fallback) for product recommendations, with a cold-start popularity fallback for users with fewer than 5 events.

### Rationale
- **Personalisation** — SVD discovers latent user–item affinity patterns across the entire user base, not just the individual user's history.
- **Cold-start handled** — users with sparse history get category-affinity + popularity-ranked products instead of empty results.
- **No separate model training** — CF runs at inference time on the current interaction matrix; no separate `.pkl` model to maintain.
- **Caching** — recommendations are cached in Redis for 1 hour, making subsequent calls instantaneous.

### Alternatives Considered
- **Content-based filtering** — recommend products similar to those a user has viewed; simpler but ignores cross-user signals.
- **Pre-trained ALS model** (implicit library) — better for implicit feedback at large scale; over-engineered for v1.

### Trade-offs
- SVD is recomputed on every cache miss — O(users × products) computation; acceptable at v1 scale.
- scikit-surprise is optional; the sklearn TruncatedSVD fallback ensures the service always returns results.

---

## ADR-007: Next.js App Router with Server Components

**Status:** Accepted

### Decision
Use Next.js 14 App Router, favouring **Server Components** for data-fetching pages (`revalidate = 60` ISR) and Client Components only for interactive elements.

### Rationale
- **Performance** — data is fetched server-side and streamed to the client; no client-side loading spinners on initial render.
- **ISR** — dashboard data is cached at the edge and refreshed every 60 seconds, reducing backend API load.
- **TypeScript** — `lib/api.ts` provides fully typed response interfaces that catch contract mismatches at compile time.
- **Simplicity** — App Router file-based routing eliminates boilerplate routing configuration.

### Alternatives Considered
- **Vite + React SPA** — pure client-side; simpler setup but no SSR/ISR, requires client-side loading states everywhere.
- **Remix** — comparable SSR model; Next.js chosen for ecosystem maturity and familiarity.

### Trade-offs
- Server Components cannot use React hooks or browser APIs directly — requires careful component boundary design.
- `revalidate = 60` means dashboard KPIs can be up to 60 seconds stale.

---

## ADR-008: UUID Primary Keys

**Status:** Accepted

### Decision
Use UUID (`gen_random_uuid()`) as the primary key type for all tables instead of auto-incrementing integers.

### Rationale
- **Distributed-safe** — UUIDs can be generated at the application layer (`uuid4()`) before a database round-trip, enabling optimistic inserts and event pre-assignment.
- **Security** — non-sequential IDs prevent enumeration attacks on API endpoints.
- **Consistency** — the event tracking SDK can generate `event_id` client-side without requiring a DB query.

### Alternatives Considered
- **BIGSERIAL (auto-increment)** — simpler, smaller index, but sequential IDs are guessable and require a DB round-trip for pre-generation.
- **ULID** — time-sortable UUID alternative; useful for ordered pagination but adds a dependency.

### Trade-offs
- UUID indexes are larger than integer indexes (16 bytes vs. 8 bytes), slightly increasing index size.
- `gen_random_uuid()` (PostgreSQL) is used as `server_default` in addition to Python's `uuid.uuid4()` to ensure DB-side consistency.

---

## ADR-009: PII Non-Logging Policy

**Status:** Accepted

### Decision
Never log PII (email addresses, user names) at INFO level or above. Tracking tokens are stripped from all log entries.

### Rationale
- **GDPR compliance** — logs are often retained in aggregation systems (e.g. Datadog, CloudWatch) that have longer retention than application data.
- **Data minimisation** — logging only identifiers (UUIDs) and non-sensitive metadata reduces the blast radius of a log infrastructure breach.

### Implementation
- `user_id` (UUID) is safe to log — not directly PII.
- `email`, `name`, tracking URLs are logged only at DEBUG level (disabled in production via `DEBUG=false`).

### Trade-offs
- Harder to correlate log entries directly to a customer for support purposes; requires joining on `user_id` in the database.
