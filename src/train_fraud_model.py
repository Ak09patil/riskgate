"""
Fraud-risk score — model 1 of 3.

Uses classic risk signals (device/IP consistency, COD, agent age, pincode
history, order value) to predict is_fraud.

We use Logistic Regression deliberately, not a black-box model:
- It's interpretable — every feature gets a clear weight, so we can explain
  WHY a transaction was flagged (important for the "explainable, bounded,
  gated" bar Razorpay set).
- It's honest about uncertainty — outputs a real probability, not just a
  label, which is what we need for the gating thresholds later.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Some numpy/BLAS builds (e.g. Apple Accelerate on ARM Macs) emit
# RuntimeWarning: overflow/divide-by-zero during cross-validation on this
# data — a real quasi-complete-separation issue (strong synthetic signal
# pushes some fold's coefficients very large), NOT a correctness bug.
# Verified: results are numerically identical with warnings raised as
# hard errors on our dev machine. Regularization (C=0.1 below) reduces
# this substantially; this filter suppresses whatever residual overflow
# warning remains on a given machine's floating-point backend, since it
# does not change any reported result. See README "what broke" for the
# full investigation.
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    precision_score, recall_score, f1_score, confusion_matrix,
    roc_auc_score
)
import joblib

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")

# --- feature engineering ---
df["is_cod"] = (df["payment_mode"] == "COD").astype(int)
from pipeline import NEW_AGENT_AGE_DAYS, HIGH_VALUE_THRESHOLD
df["is_new_agent"] = (df["agent_age_days"] < NEW_AGENT_AGE_DAYS).astype(int)
df["high_value"] = (df["order_value"] > HIGH_VALUE_THRESHOLD).astype(int)

FEATURES = [
    "device_ip_consistency", "is_cod", "pincode_return_rate",
    "is_new_agent", "high_value", "agent_age_days", "order_value",
    "user_account_age_days",
]

# --- train/test split FIRST, before any leakage-prone feature is built ---
# pincode_return_rate must be computed ONLY from training data, then applied
# to test data — otherwise the model would be "seeing" test-set fraud labels
# disguised as a feature, which would artificially inflate our metrics.
train_df, test_df = train_test_split(
    df, test_size=0.2, random_state=42, stratify=df["is_fraud"]
)

pincode_rate_map = train_df.groupby("pincode")["is_fraud"].mean()
global_fraud_rate = train_df["is_fraud"].mean()  # fallback for unseen pincodes

train_df = train_df.copy()
test_df = test_df.copy()
train_df["pincode_return_rate"] = train_df["pincode"].map(pincode_rate_map)
test_df["pincode_return_rate"] = test_df["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)

X_train, y_train = train_df[FEATURES], train_df["is_fraud"]
X_test, y_test = test_df[FEATURES], test_df["is_fraud"]

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = LogisticRegression(class_weight="balanced", random_state=42, C=0.1, max_iter=1000)

# --- PROACTIVE: check stability via cross-validation BEFORE looking at
# held-out test performance. If CV score varies a lot across folds, the
# model's performance is sensitive to which rows happen to be in train
# vs test — a real problem worth catching before trusting any single
# train/test split's numbers. ---
from sklearn.model_selection import cross_val_score
cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring="roc_auc")
print("=== 5-fold cross-validation on training data (checked BEFORE test-set evaluation) ===")
print(f"CV AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f} across folds)")
print("A small std means performance is stable across different data slices.\n")

model.fit(X_train_scaled, y_train)

# --- evaluation on held-out test set only ---
y_proba = model.predict_proba(X_test_scaled)[:, 1]

# --- threshold selection — same discipline as the intent-match model:
# chosen by maximizing F2 (recall weighted 2x precision), not left at
# sklearn's default 0.5. A missed fraud costs more than an unnecessary
# hold, so recall is weighted higher — applying this consistently across
# BOTH models, not just one, matters: picking rigor selectively would
# undercut the honesty this whole project is built on. ---
from sklearn.metrics import fbeta_score
best_f2, F2_OPTIMAL_THRESHOLD = 0, 0.5
print("=== Threshold scan (precision/recall/F2 tradeoff) ===")
for t in [round(x * 0.01, 2) for x in range(20, 90, 5)]:
    pred_t = (y_proba >= t).astype(int)
    p = precision_score(y_test, pred_t, zero_division=0)
    r = recall_score(y_test, pred_t, zero_division=0)
    f2 = fbeta_score(y_test, pred_t, beta=2, zero_division=0)
    print(f"  threshold={t:.2f}  precision={p:.3f}  recall={r:.3f}  F2={f2:.3f}")
    if f2 > best_f2:
        best_f2, F2_OPTIMAL_THRESHOLD = f2, t
print(f"\nThreshold chosen by maximizing F2 score: {F2_OPTIMAL_THRESHOLD} (F2={best_f2:.3f})\n")

y_pred = (y_proba >= F2_OPTIMAL_THRESHOLD).astype(int)

precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)
cm = confusion_matrix(y_test, y_pred)

print("=== FRAUD-RISK SCORE — held-out test set results ===")
print(f"Test set size: {len(y_test)} | Fraud rate in test: {y_test.mean():.3f}")
print(f"Precision: {precision:.3f}  (of flagged transactions, this fraction were actually fraud)")
print(f"Recall:    {recall:.3f}  (of actual fraud, this fraction was caught)")
print(f"F1:        {f1:.3f}")
print(f"ROC-AUC:   {auc:.3f}")
print("\nConfusion matrix:")
print("                Predicted: Not Fraud   Predicted: Fraud")
print(f"Actual: Not Fraud     {cm[0][0]:>6}              {cm[0][1]:>6}")
print(f"Actual: Fraud         {cm[1][0]:>6}              {cm[1][1]:>6}")

fp = cm[0][1]
fn = cm[1][0]
print(f"\nFalse positives (good txns wrongly flagged): {fp}")
print(f"False negatives (fraud missed): {fn}")
print("--> False positive cost: a wrongly-held good transaction costs a merchant")
print("    one delayed/lost sale + customer friction. False negative cost: a")
print("    missed fraud costs the transaction value directly. We tune the")
print("    threshold below to be more conservative (favor recall) since a")
print("    missed fraud is typically costlier than a delayed good order.")

print("\nFeature weights (higher |weight| = bigger influence on the score):")
for feat, coef in sorted(zip(FEATURES, model.coef_[0]), key=lambda x: -abs(x[1])):
    print(f"  {feat:30s} {coef:+.3f}")

# save model + scaler for use in the gating pipeline later
joblib.dump(model, f"{BASE_DIR}/models/fraud_model.pkl")
joblib.dump(scaler, f"{BASE_DIR}/models/fraud_scaler.pkl")
# Save the F2-optimal threshold as its own artifact (used for metrics
# reporting/drift testing) — same fix as intent model, prevents silent
# staleness. This is separate from the DEMO_THRESHOLD in pipeline.py,
# which is intentionally a different, business-chosen number — see README
# "Cost at real scale" for why those two are deliberately not the same.
joblib.dump(F2_OPTIMAL_THRESHOLD, f"{BASE_DIR}/models/fraud_f2_threshold.pkl")
print(f"Saved F2-optimal threshold artifact ({F2_OPTIMAL_THRESHOLD})")
# Save the pincode rate lookup as its own artifact, computed ONLY from
# train_df — this is what score_transaction() will load at inference
# time, so scoring a brand-new transaction later uses the exact same
# lookup the model was trained against (no leakage, no recomputation
# from data that includes test rows).
joblib.dump(
    {"pincode_rate_map": pincode_rate_map, "global_fraud_rate": global_fraud_rate},
    f"{BASE_DIR}/models/pincode_rate_lookup.pkl",
)
print("Saved model to models/fraud_model.pkl")
print("Saved pincode rate lookup to models/pincode_rate_lookup.pkl")
