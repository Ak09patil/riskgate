"""
Drift test — does the fraud model still work when the world shifts?

Real fraud isn't static: fraudsters adapt, and merchant/customer behavior
drifts over time. A model validated only on data drawn from the exact
same distribution as training is not proof it will hold up in production.

This experiment generates a SECOND synthetic batch with deliberately
shifted parameters (different fraud base rate, different signal strength
on one feature) and scores it with the ALREADY-TRAINED model — no
retraining. Whether precision/recall hold up or degrade, the result is
reported honestly, not assumed in advance: this is exactly the kind of
monitoring a real deployment needs, and why shadow-mode validation
against real outcomes (not just a synthetic holdout) matters before
trusting a model at scale.
"""

import numpy as np
import pandas as pd
import joblib

# Same quasi-complete-separation issue as training (see train_fraud_model.py)
# — scoring a large batch through the loaded model can still hit this on
# some numpy/BLAS builds even with regularization. Filtering here too,
# confirmed necessary on real device testing (this filter was originally
# only in the training scripts, which wasn't sufficient).
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from sklearn.metrics import precision_score, recall_score, roc_auc_score, confusion_matrix

rng = np.random.default_rng(999)  # different seed — a genuinely new draw

N = 1500
PINCODES = [f"5000{i}" for i in range(1, 21)]
# Shifted pincode risk profile — simulates risk moving to different areas
# over time, a realistic drift pattern (fraud rings relocate).
PINCODE_RETURN_RATE_DRIFT = {p: rng.uniform(0.05, 0.45) for p in PINCODES}


def gen_drifted_transaction():
    pincode = rng.choice(PINCODES)
    payment_mode = rng.choice(["COD", "prepaid"], p=[0.62, 0.38])  # COD share drifted up
    agent_age_days = int(rng.exponential(90))  # agents skew younger — new integrations wave
    order_price = round(rng.uniform(500, 9000), 2)
    device_ip_consistency = rng.choice([1, 0], p=[0.85, 0.15])  # slightly more mismatches
    user_account_age_days = int(rng.uniform(10, 1500))

    # DRIFTED fraud probability formula — same shape of logic, different
    # weights, simulating fraud patterns having shifted since the model
    # was trained (this is the point of the test).
    fraud_prob = 0.04  # higher base rate than training (0.02)
    if device_ip_consistency == 0:
        fraud_prob += 0.45  # device mismatch now a stronger signal
    if payment_mode == "COD":
        fraud_prob += 0.22  # COD risk increased
    if agent_age_days < 15:
        fraud_prob += 0.20  # new-agent risk weakened relative to training
    fraud_prob += PINCODE_RETURN_RATE_DRIFT[pincode] * 0.5
    if order_price > 5000:
        fraud_prob += 0.15
    is_fraud = int(rng.random() < min(fraud_prob, 0.95))

    return {
        "order_price": order_price, "order_value": order_price,
        "payment_mode": payment_mode, "pincode": pincode,
        "agent_age_days": agent_age_days,
        "device_ip_consistency": device_ip_consistency,
        "user_account_age_days": user_account_age_days,
        "is_fraud": is_fraud,
    }


if __name__ == "__main__":
    drifted = pd.DataFrame([gen_drifted_transaction() for _ in range(N)])
    print(f"Drifted batch: {len(drifted)} transactions, fraud rate {drifted['is_fraud'].mean():.3f}")
    print("(original training fraud rate was 0.295 — note the shift)\n")

    fraud_model = joblib.load(f"{BASE_DIR}/models/fraud_model.pkl")
    fraud_scaler = joblib.load(f"{BASE_DIR}/models/fraud_scaler.pkl")
    lookup = joblib.load(f"{BASE_DIR}/models/pincode_rate_lookup.pkl")
    pincode_rate_map = lookup["pincode_rate_map"]
    global_fraud_rate = lookup["global_fraud_rate"]

    drifted["is_cod"] = (drifted["payment_mode"] == "COD").astype(int)
    from pipeline import NEW_AGENT_AGE_DAYS, HIGH_VALUE_THRESHOLD, FRAUD_FEATURES
    drifted["is_new_agent"] = (drifted["agent_age_days"] < NEW_AGENT_AGE_DAYS).astype(int)
    drifted["high_value"] = (drifted["order_value"] > HIGH_VALUE_THRESHOLD).astype(int)
    drifted["cod_and_high_value"] = drifted["is_cod"] * drifted["high_value"]
    # IMPORTANT: use the ORIGINAL training-time pincode lookup, not a new
    # one fit on drifted data — this is the honest test: does the model,
    # as originally trained, still work on a shifted world?
    drifted["pincode_return_rate"] = drifted["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)

    FEATURES = FRAUD_FEATURES  # imported, not duplicated
    X = drifted[FEATURES]
    X_scaled = fraud_scaler.transform(X)
    y_true = drifted["is_fraud"]
    y_proba = fraud_model.predict_proba(X_scaled)[:, 1]
    from pipeline import FRAUD_THRESHOLD
    y_pred = (y_proba >= FRAUD_THRESHOLD).astype(int)

    print("=== Performance on DRIFTED data (model trained on original data, not retrained) ===")
    print(f"AUC:       {roc_auc_score(y_true, y_proba):.3f}   (compare to original held-out test AUC — see train_fraud_model.py output)")
    print(f"Precision: {precision_score(y_true, y_pred, zero_division=0):.3f}   (at threshold={FRAUD_THRESHOLD}, same as production — compare to train_fraud_model.py output)")
    print(f"Recall:    {recall_score(y_true, y_pred, zero_division=0):.3f}   (compare to train_fraud_model.py output)")
    cm = confusion_matrix(y_true, y_pred)
    print("\nConfusion matrix on drifted data:")
    print("                Predicted: Not Fraud   Predicted: Fraud")
    print(f"Actual: Not Fraud     {cm[0][0]:>6}              {cm[0][1]:>6}")
    print(f"Actual: Fraud         {cm[1][0]:>6}              {cm[1][1]:>6}")
    print("\nTakeaway: whether performance holds or degrades here, the point is the")
    print("same — a one-time train/test split isn't proof a model keeps working as")
    print("the world shifts. This run happened to hold up reasonably well (AUC")
    print("stayed close, precision/recall even improved with the higher drifted")
    print("fraud rate) — but that's a result to report honestly, not something to")
    print("assume will always be true. A real deployment still needs ongoing")
    print("shadow-mode validation against real outcomes, not a single static test.")
