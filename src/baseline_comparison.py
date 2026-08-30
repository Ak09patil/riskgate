"""
Baseline comparison — the question a senior reviewer asks first: does the
trained model actually beat the dumbest reasonable rule, and by how much?

Without this, an AUC number has no reference point. This compares the
fraud model against a simple hand-written rule using the same features it
was trained on, evaluated on the exact same held-out test set.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Same fix as drift_test.py / train_fraud_model.py — see there for why.
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, roc_auc_score, fbeta_score

from pipeline import NEW_AGENT_AGE_DAYS, HIGH_VALUE_THRESHOLD, FRAUD_FEATURES

df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["is_fraud"])

pincode_rate_map = train_df.groupby("pincode")["is_fraud"].mean()
global_fraud_rate = train_df["is_fraud"].mean()
test_df = test_df.copy()
test_df["pincode_return_rate"] = test_df["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)
test_df["is_cod"] = (test_df["payment_mode"] == "COD").astype(int)
test_df["is_new_agent"] = (test_df["agent_age_days"] < NEW_AGENT_AGE_DAYS).astype(int)
test_df["high_value"] = (test_df["order_value"] > HIGH_VALUE_THRESHOLD).astype(int)
test_df["cod_and_high_value"] = test_df["is_cod"] * test_df["high_value"]

y_test = test_df["is_fraud"]

# --- Baseline: simple hand-written rule using the SAME features the model
# sees, no learning involved. "Flag if COD AND device mismatch AND new
# agent" — a rule any risk analyst could write in five minutes. ---
baseline_pred = (
    (test_df["is_cod"] == 1)
    & (test_df["device_ip_consistency"] == 0)
    & (test_df["is_new_agent"] == 1)
).astype(int)

print("=== BASELINE: simple rule (COD + device mismatch + new agent) ===")
print(f"Precision: {precision_score(y_test, baseline_pred, zero_division=0):.3f}")
print(f"Recall:    {recall_score(y_test, baseline_pred, zero_division=0):.3f}")
print(f"F2:        {fbeta_score(y_test, baseline_pred, beta=2, zero_division=0):.3f}")
print(f"Flags {baseline_pred.mean()*100:.1f}% of all transactions")

# --- Trained model, at the SAME F2-optimal threshold used for its
# reported metrics, on the SAME test set ---
FEATURES = FRAUD_FEATURES  # imported, not duplicated
model = joblib.load(f"{BASE_DIR}/models/fraud_model.pkl")
scaler = joblib.load(f"{BASE_DIR}/models/fraud_scaler.pkl")
X_test_scaled = scaler.transform(test_df[FEATURES])
y_proba = model.predict_proba(X_test_scaled)[:, 1]
model_pred = (y_proba >= 0.3).astype(int)

print("\n=== MODEL: logistic regression, F2-optimal threshold (0.3) ===")
print(f"Precision: {precision_score(y_test, model_pred, zero_division=0):.3f}")
print(f"Recall:    {recall_score(y_test, model_pred, zero_division=0):.3f}")
print(f"F2:        {fbeta_score(y_test, model_pred, beta=2, zero_division=0):.3f}")
print(f"AUC:       {roc_auc_score(y_test, y_proba):.3f}")
print(f"Flags {model_pred.mean()*100:.1f}% of all transactions")

baseline_f2 = fbeta_score(y_test, baseline_pred, beta=2, zero_division=0)
model_f2 = fbeta_score(y_test, model_pred, beta=2, zero_division=0)
print("\n=== Takeaway ===")
print(f"Model F2 ({model_f2:.3f}) vs baseline F2 ({baseline_f2:.3f}): "
      f"{'model beats baseline' if model_f2 > baseline_f2 else 'baseline is competitive — model complexity is NOT clearly earning its keep'}")
print("This comparison is what justifies (or doesn't) using a trained model")
print("at all instead of a simple, fully-transparent rule a risk analyst")
print("could write and audit by hand.")
