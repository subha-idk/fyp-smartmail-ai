# 6. System Workflows

## 6.1 Event Ingestion Flow

How a single user action travels from the browser to persistent storage.

```mermaid
sequenceDiagram
    participant SDK as Storefront SDK
    participant API as FastAPI /api/track
    participant Redis as Redis Stream (events:raw)
    participant Worker as Event Worker
    participant PG as PostgreSQL

    SDK->>API: POST /api/track {event_payload}
    API->>API: Validate X-API-Key + rate limit
    API->>API: Generate event_id (UUID)
    API->>Redis: XADD events:raw {payload JSON}
    API-->>SDK: 202 Accepted {event_id}

    Note over Worker: Background asyncio Task
    Worker->>Redis: XREADGROUP (batch up to 50)
    Worker->>Worker: Parse + validate payloads
    Worker->>PG: Bulk INSERT events
    Worker->>Redis: XACK (acknowledge messages)

    alt Bulk INSERT fails
        Worker->>Worker: Sequential retry per event
        Worker->>PG: INSERT single event
        alt Event fails again
            Worker->>Redis: XADD events:failed (dead-letter)
        end
    end
```

**Key behaviours:**
- The HTTP response is returned immediately after the Redis `XADD` — the caller is never blocked by database I/O.
- The worker uses a **consumer group** (`event_workers`) so multiple worker replicas can share the load.
- Failed events land in `events:failed` stream for manual inspection or replay.

---

## 6.2 Full Email Pipeline Flow

The complete journey from a campaign trigger to email delivery and attribution tracking.

```mermaid
sequenceDiagram
    participant SCH as APScheduler (every 30 min)
    participant ES as EmailService
    participant DS as DecisionService
    participant Redis as Redis (cooldowns)
    participant RS as RecommendationService
    participant AS as AnalyticsService
    participant LS as LLMService
    participant GEM as Gemini API
    participant SMTP as SendGrid / SMTP
    participant PG as PostgreSQL

    SCH->>ES: trigger_email_pipeline(user_id)
    ES->>DS: decide_email_type(user_id)
    DS->>Redis: EXISTS cooldown:{user_id}

    alt Cooldown active
        DS-->>ES: {cooldown_active: true}
        ES-->>SCH: {status: "skipped"}
    else No cooldown
        DS->>PG: SELECT user_profiles WHERE user_id=?
        DS->>DS: Evaluate 7 priority rules
        DS-->>ES: {email_type: "retention"}
        DS->>Redis: SETEX cooldown:{user_id} TTL

        ES->>RS: get_recommendations(user_id, n=1)
        RS->>Redis: GET recommend:{user_id}:1
        alt Cache hit
            RS-->>ES: [product]
        else Cache miss
            RS->>PG: SELECT events (interactions)
            RS->>RS: Run SVD / TruncatedSVD
            RS->>Redis: SETEX recommend:{user_id}:1 3600
            RS-->>ES: [product]
        end

        ES->>AS: build_user_profile(user_id)
        AS->>PG: SELECT events WHERE user_id=?
        AS-->>ES: UserProfile

        ES->>PG: INSERT email_logs (status=sending)
        ES->>LS: generate_email(profile, product, email_type)
        LS->>LS: Load prompt template (.txt)
        LS->>LS: Format variables
        LS->>GEM: generate_content(prompt)
        GEM-->>LS: {subject, html_body, plain_body}
        LS->>PG: UPDATE email_logs SET subject, tokens_used
        LS-->>ES: email_data

        ES->>ES: inject_tracking(html, open_token, click_token)
        ES->>SMTP: send(to, subject, tracked_html, plain)
        SMTP-->>ES: success

        ES->>PG: UPDATE email_logs SET status=sent
        ES->>Redis: SETEX cooldown:{user_id}
        ES-->>SCH: {log_id, status: "sent", email_type, subject}
    end
```

---

## 6.3 Email Open / Click Tracking Flow

How engagement events are captured and fed back into the system.

```mermaid
sequenceDiagram
    participant Email as User's Email Client
    participant Track as GET /api/track/open or /click
    participant PG as PostgreSQL
    participant Redis as Redis Stream

    Email->>Track: GET /api/track/open/{token} (pixel load)
    Track->>PG: SELECT email_logs WHERE open_token=?
    alt Already opened
        Track-->>Email: 200 OK (1x1 GIF, no event)
    else First open
        Track->>PG: UPDATE SET status=opened, opened_at=now()
        Track->>Redis: XADD events:raw {email_open event}
        Track-->>Email: 200 OK (1x1 GIF)
    end

    Email->>Track: GET /api/track/click/{token}?redirect=URL
    Track->>PG: SELECT email_logs WHERE click_token=?
    alt Already clicked
        Track-->>Email: 302 Redirect (no event)
    else First click
        Track->>PG: UPDATE SET status=clicked, clicked_at=now()
        Track->>Redis: XADD events:raw {email_click event}
        Track-->>Email: 302 Redirect → original URL
    end
```

---

## 6.4 Analytics Refresh Flow

How user profiles are continuously rebuilt from raw events.

```
APScheduler (every 15 min)
    ↓
refresh_analytics_job()
    ↓
For each user_id in users table:
    AnalyticsService.build_user_profile(session, user_id)
        ↓
        SELECT * FROM events WHERE user_id = ? ORDER BY timestamp DESC
        ↓
        Compute:
          - total_events, total_purchases, total_spend
          - last_active_at, days_since_last_purchase
          - preferred_categories (Counter over event categories)
          - top_viewed_products (Counter over product_view events)
          - engagement_score (recency + frequency + monetary formula)
          - RFM scores
        ↓
        UPSERT INTO user_profiles
    ↓
    COMMIT (per user, to release locks early)
```

---

## 6.5 ML Prediction Refresh Flow

How churn risk and purchase probability are kept current.

```
APScheduler (every 1 hour)
    ↓
ml_prediction_refresh_job()
    ↓
For each user_id in users table:
    MLService.run_full_prediction(session, user_id)
        ↓
        1. AnalyticsService.build_user_profile() → UserProfile
        2. AnalyticsService.get_rolling_event_counts() → {7d, 30d counts}
        3. Construct 12-feature vector
        4. MLService.predict_churn(features)
              ↓ MLService.get_model("churn")
                    → Check Redis ml:active_model:churn
                    → Load churn_v{N}.pkl if version changed
              ↓ model.predict_proba() → churn_risk float
        5. MLService.predict_purchase_intent(features)
              → intent_v{N}.pkl → purchase_probability float
        6. UPDATE user_profiles SET churn_risk, purchase_probability
    ↓
    COMMIT
```

---

## 6.6 Weekly ML Retraining Flow

```
APScheduler (Sunday 02:00 UTC)
    ↓
weekly_retrain_job()
    ↓
Phase 1 — Feature Engineering:
    feature_pipeline.get_features_df(session)
        ↓
        Rebuild all user_profiles
        ↓
        Compute rolling stats per user
        ↓
        Assign labels:
          churned = 1 if days_since_last_active > 60
          converted = 1 if purchase within 7 days of product_view
        ↓
        Save → churn_features.csv, intent_features.csv
    ↓
Phase 2 — Training:
    train_churn():
        Load churn_features.csv
        Stratified 80/20 split
        RandomForestClassifier(n_estimators=100, max_depth=10).fit()
        Evaluate: accuracy, F1, AUC on test set
        joblib.dump(model, ml/models/churn_v{N}.pkl)
        Log metrics → model_logs table
        UPDATE Redis ml:active_model:churn → v{N}
    ↓
    train_intent():
        (Same flow with LogisticRegression and intent_features.csv)
```

---

## 6.7 User Journey — Dashboard Operator

How a marketing analyst uses the dashboard to understand and act on customer data.

```
1. Open dashboard (/) 
   → KPI cards: total users, avg engagement, emails sent, conversion rate
   → Area chart: daily event volume (last 30 days)

2. Navigate to /users
   → Paginated table: email, name, engagement score, churn risk, purchase probability
   → Search by name or email
   → Click a user row → /users/[id]

3. User detail page (/users/[id])
   → Full profile: RFM scores, preferred categories, top products
   → Engagement badge (green/yellow/red)
   → Churn risk bar
   → Top product recommendations
   → "Send Email" button → POST /api/send-email/{id}
      → Real-time response: email type sent, subject, tokens used

4. Navigate to /campaigns
   → Email log table: type, subject, status, open/click timestamps
   → Verify delivery, open, and click attribution

5. Navigate to /analytics
   → Event trend charts filtered by type and time range
```

---

## 6.8 Recommendation System — Detailed Logic

```
get_recommendations(user_id, n=3)
    ↓
Step 1: Check Redis cache (recommend:{user_id}:{n})
        → Cache HIT: fetch products by ID, return immediately
    ↓
Step 2: Fetch UserProfile → total_events
        Fetch exclude_ids (already purchased or carted products)
    ↓
Step 3: Cold-start check (total_events < 5)
        → get_cold_start_ids():
            (a) Top products in user's preferred_categories[0] by event count
            (b) Fallback: overall most-popular active products
    ↓
Step 4 (warm users): Collaborative Filtering
        Build interaction matrix:
            purchase events → score 5.0
            cart_add events → score 3.0
            product_view events → score 1.0
        Aggregate per (user, product) pair
    ↓
        If scikit-surprise available:
            SVD.fit(full trainset)
            predict scores for all candidate products
        Else (sklearn fallback):
            TruncatedSVD(n_components=min(10, ...))
            Reconstruct ratings matrix
            Extract user row → rank candidates
    ↓
Step 5: Fill shortfall with cold-start if SVD returns < n results
    ↓
Step 6: Fetch Product objects from PostgreSQL
        Cache in Redis (TTL 3600s)
        Return ordered list
```
