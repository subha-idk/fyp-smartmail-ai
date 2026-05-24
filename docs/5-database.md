# 5. Database Design

## Overview

- **Database:** PostgreSQL 16
- **Driver:** `asyncpg` (async) via SQLAlchemy 2.0
- **Primary keys:** UUID (`gen_random_uuid()`) on all tables
- **Migrations:** Alembic (`alembic upgrade head`)
- **Timestamps:** All timestamps stored as `TIMESTAMPTZ`

---

## Entity-Relationship Diagram

```mermaid
erDiagram
    users {
        UUID id PK
        VARCHAR email
        VARCHAR name
        VARCHAR country
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    products {
        UUID id PK
        VARCHAR name
        VARCHAR category
        NUMERIC price
        INTEGER stock
        BOOLEAN is_active
        TIMESTAMPTZ created_at
    }

    events {
        UUID id PK
        UUID user_id FK
        VARCHAR event_type
        UUID product_id FK
        VARCHAR session_id
        VARCHAR category
        JSONB metadata
        TIMESTAMPTZ timestamp
    }

    user_profiles {
        UUID user_id PK FK
        INTEGER total_events
        INTEGER total_purchases
        NUMERIC total_spend
        TIMESTAMPTZ last_active_at
        INTEGER days_since_last_purchase
        TEXT[] preferred_categories
        UUID[] top_viewed_products
        NUMERIC engagement_score
        NUMERIC churn_risk
        NUMERIC purchase_probability
        INTEGER rfm_recency
        INTEGER rfm_frequency
        NUMERIC rfm_monetary
        TIMESTAMPTZ updated_at
    }

    email_campaigns {
        UUID id PK
        VARCHAR name
        VARCHAR type
        TIMESTAMPTZ created_at
    }

    email_logs {
        UUID id PK
        UUID user_id FK
        UUID campaign_id FK
        VARCHAR email_type
        TEXT subject
        VARCHAR status
        VARCHAR open_token
        VARCHAR click_token
        TIMESTAMPTZ sent_at
        TIMESTAMPTZ opened_at
        TIMESTAMPTZ clicked_at
        INTEGER tokens_used
    }

    model_logs {
        UUID id PK
        VARCHAR model_name
        VARCHAR version
        NUMERIC accuracy
        NUMERIC f1_score
        NUMERIC auc_score
        TIMESTAMPTZ trained_at
    }

    users ||--o{ events : "performs"
    users ||--|| user_profiles : "has"
    users ||--o{ email_logs : "receives"
    products ||--o{ events : "referenced in"
    email_campaigns ||--o{ email_logs : "generates"
```

---

## Table Definitions

### `users`

Stores all registered customers.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, `gen_random_uuid()` | Unique identifier |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Customer email address |
| `name` | VARCHAR(255) | nullable | Display name |
| `country` | VARCHAR(10) | nullable | ISO 3166-1 country code |
| `created_at` | TIMESTAMPTZ | default `now()` | Account creation time |
| `updated_at` | TIMESTAMPTZ | default `now()`, on update | Last modification time |

**Relationships:** One-to-many with `events`, `email_logs`; one-to-one with `user_profiles`.

---

### `products`

Stores the product catalogue.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Product name |
| `category` | VARCHAR(100) | NOT NULL | Category label (e.g. `electronics`) |
| `price` | NUMERIC(10,2) | NOT NULL | Unit price |
| `stock` | INTEGER | default 0 | Current inventory count |
| `is_active` | BOOLEAN | default `true` | Controls visibility in recommendations |
| `created_at` | TIMESTAMPTZ | default `now()` | Catalogue entry date |

**Relationships:** One-to-many with `events` (referenced products).

---

### `events`

The raw behavioural event log — the platform's primary data source.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique event identifier |
| `user_id` | UUID | FK → `users.id`, NOT NULL | Acting user |
| `event_type` | VARCHAR(50) | NOT NULL | `product_view`, `search`, `cart_add`, `cart_remove`, `purchase`, `email_open`, `email_click` |
| `product_id` | UUID | FK → `products.id`, nullable | Associated product |
| `session_id` | VARCHAR(100) | nullable | Browser session identifier |
| `category` | VARCHAR(100) | nullable | Category hint (can differ from product.category) |
| `metadata` | JSONB | default `{}` | Arbitrary extra payload |
| `timestamp` | TIMESTAMPTZ | NOT NULL, default `now()` | When the event occurred |

**Indexes:**
```sql
INDEX ix_events_user_id_timestamp ON events (user_id, timestamp DESC);
INDEX ix_events_event_type_timestamp ON events (event_type, timestamp DESC);
```

> These indexes are critical — most queries filter by `user_id + timestamp` or `event_type + timestamp`.

---

### `user_profiles`

Materialised analytical profile rebuilt by the analytics engine every 15 minutes. One row per user.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id` | UUID | PK, FK → `users.id` | Identifies the user (1:1) |
| `total_events` | INTEGER | default 0 | Lifetime event count |
| `total_purchases` | INTEGER | default 0 | Lifetime purchase count |
| `total_spend` | NUMERIC(12,2) | default 0 | Cumulative revenue from this user |
| `last_active_at` | TIMESTAMPTZ | nullable | Most recent event timestamp |
| `days_since_last_purchase` | INTEGER | nullable | Integer days since last `purchase` event |
| `preferred_categories` | TEXT[] | nullable | Ordered list of category affinities |
| `top_viewed_products` | UUID[] | nullable | Top 10 most-viewed product IDs |
| `engagement_score` | NUMERIC(5,2) | nullable | Composite 0–100 engagement metric |
| `churn_risk` | NUMERIC(5,4) | nullable | ML output ∈ [0, 1] |
| `purchase_probability` | NUMERIC(5,4) | nullable | ML output ∈ [0, 1] |
| `rfm_recency` | INTEGER | nullable | Days since last purchase (RFM R) |
| `rfm_frequency` | INTEGER | nullable | Total purchases (RFM F) |
| `rfm_monetary` | NUMERIC(12,2) | nullable | Total spend (RFM M) |
| `updated_at` | TIMESTAMPTZ | auto-updated | Last profile rebuild time |

**Note:** `churn_risk` and `purchase_probability` are `NULL` until the first ML inference run completes for that user.

---

### `email_campaigns`

Campaign metadata (grouping for email logs).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique campaign identifier |
| `name` | VARCHAR(255) | NOT NULL | Human-readable campaign name |
| `type` | VARCHAR(50) | NOT NULL | `retention`, `abandoned_cart`, `recommendation`, `upsell`, `review_request` |
| `created_at` | TIMESTAMPTZ | default `now()` | Campaign creation date |

**Relationships:** One-to-many with `email_logs`.

---

### `email_logs`

Full audit log of every email sent, with open/click attribution and LLM token usage.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Unique log entry |
| `user_id` | UUID | FK → `users.id`, NOT NULL | Recipient user |
| `campaign_id` | UUID | FK → `email_campaigns.id`, nullable | Associated campaign (if batch) |
| `email_type` | VARCHAR(50) | NOT NULL | Type sent (mirrors campaign type) |
| `subject` | TEXT | nullable | Generated email subject line |
| `status` | VARCHAR(20) | default `'sent'` | `sending`, `sent`, `opened`, `clicked`, `failed`, `bounced` |
| `open_token` | VARCHAR(100) | UNIQUE, nullable | UUID token embedded in tracking pixel |
| `click_token` | VARCHAR(100) | UNIQUE, nullable | UUID token embedded in tracked links |
| `sent_at` | TIMESTAMPTZ | default `now()` | Dispatch timestamp |
| `opened_at` | TIMESTAMPTZ | nullable | First open timestamp |
| `clicked_at` | TIMESTAMPTZ | nullable | First click timestamp |
| `tokens_used` | INTEGER | nullable | Gemini API tokens consumed for generation |

---

### `model_logs`

*(Assumed — referenced in training scripts for metric persistence)*

Records training metrics after each retrain run for observability and drift monitoring.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | PK |
| `model_name` | VARCHAR | `churn` or `intent` |
| `version` | VARCHAR | e.g. `v3` |
| `accuracy` | NUMERIC | Test set accuracy |
| `f1_score` | NUMERIC | Weighted F1 score |
| `auc_score` | NUMERIC | Area Under ROC Curve |
| `trained_at` | TIMESTAMPTZ | When the model was trained |

---

## Key Relationships Summary

| Relationship | Cardinality | Notes |
|-------------|-------------|-------|
| `users` → `events` | 1 : many | Cascade-safe; user must exist before events |
| `users` → `user_profiles` | 1 : 1 | Profile created on first analytics run |
| `users` → `email_logs` | 1 : many | Full email history per user |
| `products` → `events` | 1 : many | `product_id` nullable (e.g. `search` events) |
| `email_campaigns` → `email_logs` | 1 : many | `campaign_id` nullable for manually triggered emails |
