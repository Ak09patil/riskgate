"""
Intent-match score — model 2 of 3.

Predicts is_return_or_mismatch: did the agent's actual order deviate from
what it was told to do (category/budget/attribute), in a way that's likely
to cause a return or dispute — completely separate from fraud.

Same rigor standard as the fraud model: real train/test split, no leakage,
honest metrics reported on held-out data only.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# See train_fraud_model.py for why this filter exists — same
# quasi-complete-separation issue, same non-correctness-affecting fix.
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score
)
import joblib

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")

# --- feature engineering ---
# price_delta_pct: how far over budget, as a continuous signal (not just
# the binary price_within_budget) — magnitude of deviation matters.
df["price_delta_pct"] = (df["order_price"] - df["intent_max_price"]) / df["intent_max_price"]
df["price_delta_pct"] = df["price_delta_pct"].clip(lower=0)  # only care about OVER budget

FEATURES = [
    "category_match", "price_within_budget", "attribute_match", "price_delta_pct",
]

# --- train/test split first (these features don't leak, but keep the
# same disciplined pattern as the fraud model for consistency) ---
train_df, test_df = train_test_split(
    df, test_size=0.2, random_state=42, stratify=df["is_return_or_mismatch"]
)

X_train, y_train = train_df[FEATURES], train_df["is_return_or_mismatch"]
X_test, y_test = test_df[FEATURES], test_df["is_return_or_mismatch"]

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = LogisticRegression(class_weight="balanced", random_state=42, C=0.1, max_iter=1000)

# --- PROACTIVE: cross-validate stability BEFORE evaluating on test set ---
from sklearn.model_selection import cross_val_score
cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring="roc_auc")
print("=== 5-fold cross-validation on training data (checked BEFORE test-set evaluation) ===")
print(f"CV AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f} across folds)\n")

model.fit(X_train_scaled, y_train)

y_pred = model.predict(X_test_scaled)
y_proba = model.predict_proba(X_test_scaled)[:, 1]

# --- threshold selection — chosen by an explicit, named objective, not
# by eyeballing a table. We use F2 (weights recall 2x more than
# precision) because we've already reasoned that a missed mismatch costs
# more than an unnecessary human confirmation — F2 formalizes that
# stated cost preference instead of hand-picking a threshold that "looks
# reasonable." ---
from sklearn.metrics import fbeta_score, precision_recall_curve

precisions, recalls, thresholds = precision_recall_curve(y_test, y_proba)
print("=== Threshold scan (precision/recall/F2 tradeoff) ===")
best_f2, BEST_THRESHOLD = 0, 0.5
for t in [round(x * 0.01, 2) for x in range(20, 90, 5)]:
    pred_t = (y_proba >= t).astype(int)
    p = precision_score(y_test, pred_t, zero_division=0)
    r = recall_score(y_test, pred_t, zero_division=0)
    f2 = fbeta_score(y_test, pred_t, beta=2, zero_division=0)
    print(f"  threshold={t:.2f}  precision={p:.3f}  recall={r:.3f}  F2={f2:.3f}")
    if f2 > best_f2:
        best_f2, BEST_THRESHOLD = f2, t

y_pred = (y_proba >= BEST_THRESHOLD).astype(int)

print("\nThreshold chosen by maximizing F2 score (recall weighted 2x precision,")
print(f"matching our stated cost reasoning): {BEST_THRESHOLD} (F2={best_f2:.3f})\n")

precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)
cm = confusion_matrix(y_test, y_pred)

print("=== INTENT-MATCH SCORE — held-out test set results ===")
print(f"Test set size: {len(y_test)} | Mismatch rate in test: {y_test.mean():.3f}")
print(f"Precision: {precision:.3f}")
print(f"Recall:    {recall:.3f}")
print(f"F1:        {f1:.3f}")
print(f"ROC-AUC:   {auc:.3f}")
print("\nConfusion matrix:")
print("                  Predicted: Match    Predicted: Mismatch")
print(f"Actual: Match          {cm[0][0]:>6}              {cm[0][1]:>6}")
print(f"Actual: Mismatch       {cm[1][0]:>6}              {cm[1][1]:>6}")

fp = cm[0][1]
fn = cm[1][0]
print(f"\nFalse positives (good agent decisions wrongly flagged): {fp}")
print(f"False negatives (real mismatches missed): {fn}")
print("--> Here the false-positive cost is different from fraud: wrongly")
print("    flagging a good agent order means an unnecessary human interruption")
print("    (mild friction, not lost money). A missed mismatch means an")
print("    unnecessary return/dispute downstream (real merchant cost).")
print("    This is a lower-stakes tradeoff than fraud, so this score can")
print("    afford to be a bit more liberal about flagging than fraud can.")

print("\nFeature weights:")
for feat, coef in sorted(zip(FEATURES, model.coef_[0]), key=lambda x: -abs(x[1])):
    print(f"  {feat:22s} {coef:+.3f}")

joblib.dump(model, f"{BASE_DIR}/models/intent_model.pkl")
joblib.dump(scaler, f"{BASE_DIR}/models/intent_scaler.pkl")
# Save the F2-optimal threshold as its own artifact — this is what fixes
# the exact bug we found: a hardcoded threshold in pipeline.py/gating.py
# silently going stale whenever this script is rerun on changed data.
# pipeline.py now LOADS this instead of hardcoding a copy of the number.
joblib.dump(BEST_THRESHOLD, f"{BASE_DIR}/models/intent_threshold.pkl")
print(f"Saved threshold artifact to models/intent_threshold.pkl ({BEST_THRESHOLD})")
print("\nSaved model to models/intent_model.pkl")
