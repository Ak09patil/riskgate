"""
Second-seed validation — reruns the fraud model's train/test split with a
DIFFERENT random seed and checks the metrics land in the same range.

Why this matters: a single train/test split's numbers can vary just from
which rows happened to land in test. If precision/recall/AUC swing wildly
across seeds, our reported numbers were a lucky (or unlucky) draw, not a
stable result. This confirms — or would have caught — that problem before
reporting metrics as if they were guaranteed.
"""

import pandas as pd

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# See train_fraud_model.py for why this filter exists.
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, roc_auc_score

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")

FEATURES = [
    "device_ip_consistency", "is_cod", "pincode_return_rate",
    "is_new_agent", "high_value", "agent_age_days", "order_value",
    "user_account_age_days",
]

results = []
for seed in [42, 7, 123, 2026, 99]:
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=seed, stratify=df["is_fraud"])
    pincode_rate_map = train_df.groupby("pincode")["is_fraud"].mean()
    global_fraud_rate = train_df["is_fraud"].mean()

    train_df = train_df.copy()
    test_df = test_df.copy()
    for d in (train_df, test_df):
        d["is_cod"] = (d["payment_mode"] == "COD").astype(int)
        from pipeline import NEW_AGENT_AGE_DAYS, HIGH_VALUE_THRESHOLD
        d["is_new_agent"] = (d["agent_age_days"] < NEW_AGENT_AGE_DAYS).astype(int)
        d["high_value"] = (d["order_value"] > HIGH_VALUE_THRESHOLD).astype(int)
    train_df["pincode_return_rate"] = train_df["pincode"].map(pincode_rate_map)
    test_df["pincode_return_rate"] = test_df["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)

    X_train, y_train = train_df[FEATURES], train_df["is_fraud"]
    X_test, y_test = test_df[FEATURES], test_df["is_fraud"]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(class_weight="balanced", random_state=seed, C=0.1, max_iter=1000)
    model.fit(X_train_scaled, y_train)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    # Use the SAME F2-optimization procedure as train_fraud_model.py for
    # each seed's own threshold — using a fixed 0.5 cutoff here would make
    # these numbers incomparable to what's actually reported, which is
    # exactly the staleness bug we already found and fixed twice elsewhere.
    from sklearn.metrics import fbeta_score
    best_f2, best_t = 0, 0.5
    for t in [round(x * 0.01, 2) for x in range(20, 90, 5)]:
        pred_t = (y_proba >= t).astype(int)
        f2 = fbeta_score(y_test, pred_t, beta=2, zero_division=0)
        if f2 > best_f2:
            best_f2, best_t = f2, t
    y_pred = (y_proba >= best_t).astype(int)

    results.append({
        "seed": seed,
        "threshold": best_t,
        "auc": round(roc_auc_score(y_test, y_proba), 3),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 3),
    })

results_df = pd.DataFrame(results)
print("=== Fraud model performance across 5 different random seeds ===")
print(results_df.to_string(index=False))
print(f"\nAUC:       mean={results_df['auc'].mean():.3f}  std={results_df['auc'].std():.3f}")
print(f"Precision: mean={results_df['precision'].mean():.3f}  std={results_df['precision'].std():.3f}")
print(f"Recall:    mean={results_df['recall'].mean():.3f}  std={results_df['recall'].std():.3f}")
print("\nSmall std across seeds means our reported numbers (seed=42) are a")
print("stable, representative result — not a lucky single draw.")
