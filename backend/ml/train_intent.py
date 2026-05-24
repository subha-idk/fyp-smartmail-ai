"""Train Intent Model — trains a LogisticRegression classifier and logs metrics to PostgreSQL."""

import asyncio
import glob
import os
import re
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

from app.database import async_session_factory
from app.models.model_log import ModelLog

# Define feature columns matching Section 5 of CONTEXT.md
FEATURE_COLS = [
    "days_since_last_active",
    "days_since_last_purchase",
    "total_events_7d",
    "total_events_30d",
    "total_purchases",
    "total_spend",
    "cart_add_count_30d",
    "purchase_count_30d",
    "engagement_score",
    "rfm_recency",
    "rfm_frequency",
    "rfm_monetary",
]


def get_next_version(model_name: str, models_dir: str) -> int:
    """Finds the next version integer for the given model_name."""
    os.makedirs(models_dir, exist_ok=True)
    files = glob.glob(os.path.join(models_dir, f"{model_name}_v*.pkl"))
    max_ver = 0
    for f in files:
        match = re.search(rf"{model_name}_v(\d+)\.pkl$", os.path.basename(f))
        if match:
            max_ver = max(max_ver, int(match.group(1)))
    return max_ver + 1


async def log_to_db(model_name: str, version: str, metrics: dict) -> None:
    """Persists model training metrics to the model_logs table."""
    async with async_session_factory() as session:
        log = ModelLog(
            model_name=model_name,
            version=version,
            metrics=metrics,
        )
        session.add(log)
        await session.commit()


async def train_intent():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "intent_features.csv")
    models_dir = os.path.join(base_dir, "models")

    if not os.path.exists(csv_path):
        print(f"Error: Feature file {csv_path} not found. Run feature_pipeline.py first.")
        return

    df = pd.read_csv(csv_path)
    if len(df) < 5:
        print("Not enough data to train intent model.")
        return

    X = df[FEATURE_COLS]
    y = df["converted"]

    # Check if there is more than 1 class
    if len(y.unique()) < 2:
        print(f"Warning: Intent target only contains one class ({y.unique()}). Model might be trivial.")

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(y.unique()) > 1 else None
    )

    # Train Logistic Regression with class weighting and scaling pipeline
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42))
    ])
    pipeline.fit(X_train, y_train)

    # Evaluate
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1] if len(pipeline.named_steps['clf'].classes_) > 1 else y_pred

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    try:
        auc_roc = roc_auc_score(y_test, y_prob)
        import math
        if math.isnan(auc_roc) or math.isinf(auc_roc):
            auc_roc = 0.5
    except ValueError:
        auc_roc = 0.5

    metrics = {
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "auc_roc": round(float(auc_roc), 4),
    }

    # Versioning & save
    next_ver = get_next_version("intent", models_dir)
    version_str = f"v{next_ver}"
    model_filename = f"intent_{version_str}.pkl"
    model_path = os.path.join(models_dir, model_filename)

    joblib.dump(pipeline, model_path)
    print(f"Saved intent model to: {model_path}")
    print(f"Metrics: {metrics}")

    # Update Redis active model key
    import redis.asyncio as aioredis
    from app.config import settings
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis_client.set("ml:active_model:intent", version_str)
        print(f"Updated Redis active model key to: {version_str}")
    finally:
        await redis_client.close()

    # Clean old versions, keep last 3
    files = glob.glob(os.path.join(models_dir, "intent_v*.pkl"))
    versioned_files = []
    for f in files:
        match = re.search(r"intent_v(\d+)\.pkl$", os.path.basename(f))
        if match:
            versioned_files.append((int(match.group(1)), f))
    versioned_files.sort(key=lambda x: x[0], reverse=True)
    if len(versioned_files) > 3:
        for ver, path in versioned_files[3:]:
            try:
                os.remove(path)
                print(f"Removed old model version: {path}")
            except Exception as e:
                print(f"Failed to remove old model version {path}: {e}")

    # Log to PostgreSQL
    await log_to_db("intent", version_str, metrics)
    print("Logged metrics to database.")


if __name__ == "__main__":
    asyncio.run(train_intent())
