# 4. API Specification

## Authentication

All endpoints (except tracking pixel and click redirect) require:

```
X-API-Key: <API_SECRET_KEY>
Content-Type: application/json
```

Rate limiting is enforced on every endpoint via the `check_rate_limit` dependency.

---

## Base URL

| Environment | URL |
|-------------|-----|
| Local development | `http://localhost:8000` |
| Docker Compose | `http://backend:8000` |

Interactive docs: `http://localhost:8000/docs` (Swagger UI)

---

## Health Check

### `GET /health`
Returns server liveness. No auth required.

**Response `200 OK`:**
```json
{ "status": "healthy" }
```

### `GET /api/health`
Returns API readiness for the frontend health indicator. No auth required.

**Response `200 OK`:**
```json
{ "status": "ok" }
```

---

## Event Tracking — `/api/track`

### `POST /api/track`
Ingests a single behavioural event into the Redis Stream.

**Request Body:**
```json
{
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "event_type": "product_view",
  "product_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "session_id": "s_abc123",
  "category": "electronics",
  "timestamp": "2026-05-20T14:32:00Z",
  "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | UUID | ✅ | ID of the user performing the action |
| `event_type` | string | ✅ | One of: `product_view`, `search`, `cart_add`, `cart_remove`, `purchase`, `email_open`, `email_click` |
| `product_id` | UUID | ❌ | Associated product (optional for `search`) |
| `session_id` | string | ❌ | Browser/app session identifier |
| `category` | string | ❌ | Product category hint |
| `timestamp` | ISO 8601 | ❌ | Defaults to server `now()` if omitted |
| `metadata` | object | ❌ | Arbitrary additional data |

**Response `202 Accepted`:**
```json
{ "status": "queued", "event_id": "3fa85f64-..." }
```

---

### `POST /api/track/batch`
Ingests up to 100 events in a single request via Redis pipeline.

**Request Body:** Array of event payloads (same schema as single event).

**Response `200 OK`:**
```json
{ "queued": 5, "failed": 0 }
```

**Error `400 Bad Request`:** Batch size exceeds 100.

---

### `GET /api/track/open/{token}`
Email open tracking pixel. Returns a 1×1 transparent GIF. No auth required (embedded in emails).

- Sets `email_logs.opened_at` and enqueues an `email_open` event.
- **Idempotent** — subsequent requests return the pixel immediately without re-firing the event.
- Response includes `Cache-Control: no-cache` headers.

**Response `200 OK`:** `image/gif`

---

### `GET /api/track/click/{token}?redirect={url}`
Email click tracking. Updates `email_logs.clicked_at`, enqueues `email_click`, then redirects the user.

- **Idempotent** — second click redirects without re-firing the event.
- If `redirect` query param is absent, redirects to `FRONTEND_URL`.

**Response `302 Found`:** Redirect to target URL.

---

## Users & Profiles — `/api/users`

### `GET /api/users`
Returns a paginated list of users with their summarised profiles.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (≥ 1) |
| `limit` | integer | 20 | Items per page (1–100) |
| `q` | string | — | Search filter on `email` or `name` (case-insensitive) |

**Response `200 OK`:**
```json
{
  "users": [
    {
      "id": "3fa85f64-...",
      "email": "alice@example.com",
      "name": "Alice",
      "country": "SG",
      "created_at": "2026-05-01T10:00:00Z",
      "profile": {
        "total_events": 47,
        "total_purchases": 3,
        "total_spend": 249.99,
        "last_active_at": "2026-05-23T18:00:00Z",
        "engagement_score": 72.5,
        "churn_risk": 0.12,
        "purchase_probability": 0.65
      }
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20
}
```

---

### `GET /api/users/{id}/profile`
Returns the full analytical profile for a specific user. If no profile exists, builds one on-demand.

**Path Parameter:** `id` — User UUID.

**Response `200 OK`:**
```json
{
  "user_id": "3fa85f64-...",
  "total_events": 47,
  "total_purchases": 3,
  "total_spend": 249.99,
  "last_active_at": "2026-05-23T18:00:00Z",
  "days_since_last_purchase": 5,
  "preferred_categories": ["electronics", "books"],
  "top_viewed_products": ["uuid1", "uuid2"],
  "engagement_score": 72.5,
  "churn_risk": 0.12,
  "purchase_probability": 0.65,
  "rfm_recency": 5,
  "rfm_frequency": 3,
  "rfm_monetary": 249.99,
  "updated_at": "2026-05-24T10:00:00Z"
}
```

**Error `404 Not Found`:** User does not exist.

---

## Analytics — `/api/analytics`

### `GET /api/analytics/summary`
Returns aggregate KPIs across all users for the dashboard.

**Response `200 OK`:**
```json
{
  "total_users": 500,
  "total_products": 120,
  "total_events": 18400,
  "total_campaigns": 12,
  "emails_sent": 340,
  "emails_opened": 128,
  "emails_clicked": 54,
  "emails_failed": 6,
  "emails_bounced": 2,
  "total_emails": 476,
  "avg_engagement_score": 61.34,
  "conversion_rate": 0.062,
  "open_rate": 38.24,
  "click_rate": 11.34
}
```

---

### `GET /api/analytics/events`
Returns daily event counts as a time series for charting.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Number of days to look back (1–90) |
| `event_type` | string | — | Filter by specific event type |
| `user_id` | UUID | — | Filter to a specific user |

**Response `200 OK`:**
```json
[
  { "date": "2026-05-01", "count": 142 },
  { "date": "2026-05-02", "count": 178 }
]
```

---

## ML Prediction — `/api/predict`

### `POST /api/predict/{user_id}`
Runs the full ML prediction pipeline for a user: builds feature vector, runs churn + intent inference, and persists results to `user_profiles`.

**Path Parameter:** `user_id` — User UUID.

**Response `200 OK`:**
```json
{
  "user_id": "3fa85f64-...",
  "churn_risk": 0.8234,
  "purchase_probability": 0.4156
}
```

---

## Recommendations — `/api/recommend`

### `GET /api/recommend/{user_id}?n=3`
Returns the top-N recommended products for a user.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n` | integer | 3 | Number of recommendations to return |

**Response `200 OK`:**
```json
[
  {
    "id": "9b1deb4d-...",
    "name": "Wireless Headphones Pro",
    "category": "electronics",
    "price": 199.99,
    "stock": 42,
    "is_active": true,
    "created_at": "2026-04-01T00:00:00Z"
  }
]
```

---

## Decision Engine — `/api/decide`

### `POST /api/decide/{user_id}`
Evaluates the decision rules and returns the recommended campaign type for a user. Does **not** send an email.

**Path Parameter:** `user_id` — User UUID.

**Response `200 OK`:**
```json
{
  "email_type": "retention",
  "rationale": "churn_risk=0.8234 exceeds threshold 0.7",
  "cooldown_active": false,
  "skip_reason": null
}
```

| Field | Description |
|-------|-------------|
| `email_type` | One of: `retention`, `abandoned_cart`, `recommendation`, `upsell`, `review_request`, or `null` |
| `rationale` | Human-readable explanation of the decision |
| `cooldown_active` | `true` if cooldown is blocking email dispatch |
| `skip_reason` | `"cooldown_active"` or `null` |

---

## Email Generation — `/api/generate-email`

### `POST /api/generate-email`
Generates a personalised email using Gemini without sending it. Useful for preview.

**Request Body:**
```json
{
  "user_id": "3fa85f64-...",
  "email_type": "retention",
  "product_id": "9b1deb4d-..."
}
```

**Response `200 OK`:**
```json
{
  "subject": "We miss you, Alice — here's 15% off",
  "html_body": "<html>...</html>",
  "plain_body": "Hi Alice, we noticed you haven't visited in 14 days...",
  "tokens_used": 487
}
```

---

## Email Delivery — `/api/send-email`

### `POST /api/send-email/{user_id}`
Executes the **full email pipeline** in sequence:
1. Decide email type (DecisionService)
2. Get product recommendation (RecommendationService)
3. Build/fetch user profile (AnalyticsService)
4. Generate email content (LLMService via Gemini)
5. Inject tracking tokens (EmailService)
6. Send via SendGrid/SMTP (EmailService)
7. Commit email log + set cooldown

**Response `200 OK` (sent):**
```json
{
  "log_id": "c1a2b3c4-...",
  "status": "sent",
  "email_type": "retention",
  "subject": "We miss you, Alice!",
  "tokens_used": 512
}
```

**Response `200 OK` (skipped — cooldown active):**
```json
{ "status": "skipped", "reason": "cooldown" }
```

**Error `404 Not Found`:** User does not exist.  
**Error `500 Internal Server Error`:** Pipeline failure (email dispatch error).

---

## Email Logs — `/api/email_logs`

### `GET /api/email_logs`
Returns paginated email history joined with user metadata.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 20 | Items per page (1–100) |

**Response `200 OK`:**
```json
{
  "logs": [
    {
      "id": "c1a2b3c4-...",
      "user_id": "3fa85f64-...",
      "user_name": "Alice",
      "user_email": "alice@example.com",
      "email_type": "retention",
      "subject": "We miss you, Alice!",
      "status": "clicked",
      "sent_at": "2026-05-24T12:00:00Z",
      "opened_at": "2026-05-24T12:05:32Z",
      "clicked_at": "2026-05-24T12:06:10Z",
      "tokens_used": 512
    }
  ],
  "total": 340
}
```
