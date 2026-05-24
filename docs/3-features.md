# 3. Features

## 3.1 Real-Time Event Tracking

**What it does:** Captures every meaningful user interaction via a lightweight REST API. Events are immediately pushed to a Redis Stream for async processing — the HTTP response is returned in < 100 ms p99.

**Tracked event types:**

| Event | Meaning |
|-------|---------|
| `product_view` | User viewed a product page |
| `search` | User submitted a search query |
| `cart_add` | Item added to cart |
| `cart_remove` | Item removed from cart |
| `purchase` | Order completed |
| `email_open` | User opened a tracked email (pixel fired) |
| `email_click` | User clicked a link inside an email |

**Endpoints:**
- `POST /api/track` — single event ingestion
- `POST /api/track/batch` — up to 100 events in a single request
- `GET /api/track/open/{token}` — 1×1 GIF tracking pixel (idempotent)
- `GET /api/track/click/{token}` — click redirect + attribution (idempotent)

**Reliability:** Failed events are dead-lettered to `events:failed` stream for later inspection.

---

## 3.2 User Profile Engine

**What it does:** Maintains a continuously updated analytical profile per user, combining raw event history with derived features.

**Computed fields:**

| Field | Description |
|-------|-------------|
| `total_events` | Lifetime event count |
| `total_purchases` | Total purchase events |
| `total_spend` | Cumulative spend (derived from product prices) |
| `last_active_at` | Timestamp of most recent event |
| `days_since_last_purchase` | Integer days |
| `preferred_categories` | Ordered list by event frequency |
| `top_viewed_products` | Top 10 most-viewed product UUIDs |
| `engagement_score` | Composite 0–100 score (see formula below) |
| `churn_risk` | ML output ∈ [0, 1] |
| `purchase_probability` | ML output ∈ [0, 1] |
| `rfm_recency` | Days since last purchase |
| `rfm_frequency` | Total purchases |
| `rfm_monetary` | Total spend |

**Engagement Score Formula:**
```
score = (recency_score × 0.35) + (frequency_score × 0.35) + (monetary_score × 0.30)

recency_score   = max(0, 100 − days_since_last_active × 2)
frequency_score = min(100, total_events_last_30d × 3)
monetary_score  = min(100, total_spend / 10)
```

**Refresh cadence:** Every 15 minutes via APScheduler (all users), or on-demand when a profile is first accessed.

---

## 3.3 ML Prediction Module

**What it does:** Two independent classifiers score every user for churn risk and purchase intent.

| Model | Algorithm | Target Label | Threshold |
|-------|-----------|-------------|-----------|
| **Churn Predictor** | Random Forest (`n_estimators=100, max_depth=10`) | `churned = 1` if `days_since_last_active > 60` | 0.7 (configurable) |
| **Intent Predictor** | Logistic Regression (`C=1.0, max_iter=500`) | `converted = 1` if purchase within 7 days of a product_view | 0.6 (configurable) |

**Feature vector (12 features, shared by both models):**
- `days_since_last_active`, `days_since_last_purchase`
- `total_events_7d`, `total_events_30d`
- `total_purchases`, `total_spend`
- `cart_add_count_30d`, `purchase_count_30d`
- `engagement_score`, `rfm_recency`, `rfm_frequency`, `rfm_monetary`

**Model versioning:**
- Saved as `ml/models/{name}_v{N}.pkl` via `joblib`.
- Active version tracked in Redis (`ml:active_model:{name}`).
- In-process cache — models are only reloaded when the version pointer changes.

**Inference refresh:** Every 1 hour via APScheduler.  
**Retraining:** Every Sunday at 02:00 UTC.

---

## 3.4 Decision Engine

**What it does:** Selects the most appropriate email campaign type for a user by evaluating rules in strict priority order.

| Priority | Condition | Campaign Type |
|----------|-----------|--------------|
| 1 | Email cooldown active (`EMAIL_COOLDOWN_HOURS`, default 24 h) | Skip |
| 2 | `churn_risk > CHURN_RISK_THRESHOLD` (default 0.7) | `retention` |
| 3 | Cart items exist + last `cart_add` > `CART_ABANDON_HOURS` (default 24 h) ago + no purchase since | `abandoned_cart` |
| 4 | `purchase_probability > PURCHASE_PROB_THRESHOLD` (default 0.6) | `recommendation` |
| 5 | `total_spend > TOP_SPENDER_THRESHOLD` (default $500) | `upsell` |
| 6 | Last purchase was 7–14 days ago | `review_request` |
| 7 | Default | `recommendation` |

**Cooldown mechanism:** A Redis key (`cooldown:{user_id}`) is set after every successful send, with TTL equal to `EMAIL_COOLDOWN_HOURS`. Cleared automatically on expiry; also removed on failed dispatch.

---

## 3.5 Recommendation Engine

**What it does:** Surfaces the top-N most relevant products for a user using collaborative filtering.

**Algorithm:**
1. Build a user–item interaction matrix from `purchase`, `cart_add`, and `product_view` events (scores: 5 / 3 / 1).
2. Apply **SVD** (via scikit-surprise, if installed) or **TruncatedSVD** (sklearn fallback) to learn latent factors.
3. Score all active products not already purchased or carted by the user.
4. Return top-N ranked by predicted affinity.

**Cold-start fallback** (< 5 events): Return most-popular products from the user's preferred category; fall back to overall site popularity.

**Caching:** Results cached in Redis at `recommend:{user_id}:{n}` with 1-hour TTL.

---

## 3.6 LLM Email Generation

**What it does:** Calls Google Gemini to generate a concise, personalised marketing email from a structured prompt.

**Supported email types and unique prompt variables:**

| Email Type | Unique Variables |
|------------|-----------------|
| `retention` | `days_inactive`, `discount_offer` |
| `abandoned_cart` | `cart_items`, `hours_since_abandoned` |
| `recommendation` | — |
| `upsell` | `user_tier`, `total_spend` |
| `review_request` | — |

**Shared variables (all types):** `user_name`, `product_name`, `product_price`, `preferred_category`

**Gemini interaction:**
- Model: `gemini-2.0-flash` (configurable)
- System instruction: copywriter persona instructed to return only valid JSON (`subject`, `html_body`, `plain_body`)
- Token usage logged to `email_logs.tokens_used` on every call
- Monthly budget cap: 5,000,000 tokens (configurable)

**Fallback:** On any Gemini API error, the raw prompt template is rendered as plain text and wrapped in basic HTML — ensuring email delivery never fully fails.

---

## 3.7 Email Delivery & Tracking

**What it does:** Sends the generated email via SendGrid (production) or SMTP (development/self-hosted), with tracking injected automatically.

**Tracking injection (automatic):**
- **Open pixel** — `<img src="{BACKEND_URL}/api/track/open/{token}" width="1" height="1" />` appended before `</body>`
- **Click redirect** — all `<a href>` links replaced with `{BACKEND_URL}/api/track/click/{click_token}?redirect={original_url}`

**Email status lifecycle:**
```
sending → sent → opened → clicked
                 ↘ failed
                 ↘ bounced
```

**Idempotency:** Both open and click tracking endpoints are idempotent — a second pixel fire or click does not create a duplicate event.

---

## 3.8 Analytics Dashboard

**What it does:** A Next.js 14 App Router single-page application for marketing teams to monitor the platform.

**Pages and data sources:**

| Route | Page | Data Source |
|-------|------|------------|
| `/` | Dashboard overview | `GET /api/analytics/summary` |
| `/users` | Paginated users table with search | `GET /api/users?page=&limit=&q=` |
| `/users/[id]` | User detail — profile, scores, recommendations | `GET /api/users/{id}/profile`, `GET /api/recommend/{id}` |
| `/campaigns` | Email log table — status, open/click times, tokens | `GET /api/email_logs` |
| `/analytics` | Event charts and trends | `GET /api/analytics/events` |
| `/demo` | Interactive demo panel | Various |

**Key components:**
- `<KpiCard>` — stat card with delta indicator (↑/↓ trend)
- `<EngagementBadge score={n} />` — colour-coded pill (green / yellow / red)
- `<ChurnRiskBar risk={n} />` — horizontal progress bar
- `<OverviewChart data={series} />` — Recharts area chart for daily event volume
- `<AnalyticsCharts />` — multi-series charts for campaign metrics
- `<SendEmailButton />` — triggers the full email pipeline for a selected user

---

## 3.9 Background Job Scheduler

Four recurring jobs managed by APScheduler (AsyncIO mode):

| Job | Schedule | Action |
|-----|----------|--------|
| Analytics refresh | Every 15 min | Rebuild all `user_profiles` |
| ML prediction refresh | Every 1 hour | Re-score all users with loaded models |
| Campaign trigger | Every 30 min | Run decision engine for up to 50 active users; send due emails |
| Weekly retrain | Sunday 02:00 UTC | Rebuild feature CSVs + retrain churn and intent models |

---

## 3.10 Closed Feedback Loop

The platform forms a complete closed loop:

```
User behaviour (events)
        ↓
User profile + RFM features
        ↓
ML models → churn / intent scores
        ↓
Decision engine → email type
        ↓
Recommendation engine → product
        ↓
LLM → personalised email
        ↓
Email sent → open/click events
        ↓  (back to top)
User behaviour (events)
```

Open and click events from emails re-enter the same `events:raw` stream, updating engagement scores and serving as positive training labels for the next weekly retrain.
