# 1. Project Overview

## Problem Statement

E-commerce marketing teams face three compounding failures today:

1. **Generic messaging** — campaigns are batch-blasted with no awareness of where a customer is in their lifecycle. Every customer receives the same email regardless of their recent behaviour.
2. **Reactive decisions** — churn and purchase-intent signals are spotted too late, after the conversion window has already closed.
3. **Disconnected tooling** — behavioural data, ML models, and email tools live in separate systems with no shared state, making it impossible to act on signals in real time.

**The result:** low open rates, poor click-through rates (CTR), wasted marketing budget, and missed revenue.

---

## Solution

SmartMail AI+ is an **event-driven, AI-powered customer engagement platform** that:

- Ingests every meaningful user action (page views, cart events, purchases, email interactions) in real time via a lightweight REST + Redis Streams pipeline.
- Aggregates events into continuously updated **user profiles** (RFM scores, engagement index, category affinity).
- Runs two **scikit-learn classifiers** — a Random Forest churn predictor and a Logistic Regression purchase-intent predictor — to score every user on a regular schedule.
- Uses a **hybrid rule + ML decision engine** to select the most relevant campaign type for each user (retention, abandoned cart, recommendation, upsell, review request).
- Generates a fully personalised **HTML email** (subject + body) via the Google Gemini API using structured prompt templates.
- Injects **open-tracking pixels and click-redirect links** into the email, creating a closed feedback loop where engagement events feed back into the ML training data.
- Presents all metrics on a **Next.js analytics dashboard** for marketing and growth teams.

---

## Target Users

### Primary Users
| Persona | Need |
|---------|------|
| **E-commerce marketing team** (2–50 person companies) | Automated lifecycle campaigns without manual segmentation |
| **CRM manager** | Unified view of customer engagement and campaign performance |

### Secondary Users
| Persona | Need |
|---------|------|
| **Growth / retention analyst** | Behavioural insight dashboards, ML score distributions |
| **Developer / integrator** | REST tracking SDK to embed in storefronts |

---

## System Goals

| Goal | Metric | Target |
|------|--------|--------|
| Increase email relevance | Open rate | ≥ 35% |
| Drive click engagement | CTR | ≥ 12% |
| Improve revenue impact | Conversion rate | ≥ 5% |
| Predict churn accurately | Model F1 score | ≥ 0.80 |
| Minimise response latency | Event → email dispatch | < 5 minutes |
| Handle scale | Events/day | 10,000 (v1); horizontally scalable to 1 M |
| Reliability | Uptime | 99.5% |
| Data safety | Event loss on restart | Zero (Redis persistence) |

---

## Scope

### In Scope — v1.0
- Real-time behavioural event ingestion
- User profile aggregation and feature engineering
- Churn risk + purchase intent prediction (ML)
- Rule + ML hybrid decision engine
- Collaborative-filtering product recommendations
- LLM-generated personalised email content (Gemini API)
- Transactional email delivery (SMTP / SendGrid)
- Analytics dashboard (Next.js)
- Feedback loop: open/click events feed back into model training

### Out of Scope — v1.0
- SMS / push notification channels
- A/B testing framework
- Multi-language email generation
- Self-serve onboarding / SaaS billing
- Native mobile app
