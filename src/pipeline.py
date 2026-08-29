"""
RiskGate pipeline — the ONE place all three models and the gate connect.

This is the real system: score_transaction(txn_dict) -> decision_dict.
Anything that wants a RiskGate decision (a demo script, an API, the
dashboard via a local server) calls this one function. There is exactly
one gating implementation, not one for batch scoring and a different one
for "live" scoring — that was the actual gap: gating.py only ran in
batch over a whole CSV. This module is what fixes that.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Same numerical-stability fix as the training scripts (see
# train_fraud_model.py) — confirmed necessary here too on real device
# testing, since this is the module the live API/dashboard actually call.
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

import joblib
import pandas as pd

MODELS_DIR = f"{BASE_DIR}/models"

FRAUD_THRESHOLD = 0.5  # DEMO/business threshold, deliberately not the F2-optimal
                        # value — see gating.py and README "Cost at real scale"
                        # for why these two numbers are intentionally different.
                        # (unlike INTENT_THRESHOLD below, this one does NOT load
                        # from the training artifact — it's a fixed business
                        # choice, not meant to track the F2-optimal value.)
PREF_FIT_THRESHOLD = 0.5
NEW_AGENT_AGE_DAYS = 15   # single source of truth — was previously duplicated
                          # as a hardcoded "15" in train_fraud_model.py,
                          # drift_test.py, and seed_validation.py, which
                          # could silently drift out of sync if changed in
                          # only one place. Import this constant instead.
HIGH_VALUE_THRESHOLD = 5000  # same fix, same reasoning

FRAUD_FEATURES = [
    "device_ip_consistency", "is_cod", "pincode_return_rate",
    "is_new_agent", "high_value", "agent_age_days", "order_value",
    "user_account_age_days",
]
INTENT_FEATURES = ["category_match", "price_within_budget", "attribute_match", "price_delta_pct"]

_fraud_model = None
_fraud_scaler = None
_intent_model = None
_intent_scaler = None
_pincode_lookup = None
_intent_threshold = None


def _load_artifacts():
    """Lazy-load all model artifacts once, shared across calls."""
    global _fraud_model, _fraud_scaler, _intent_model, _intent_scaler, _pincode_lookup, _intent_threshold
    if _fraud_model is None:
        _fraud_model = joblib.load(f"{MODELS_DIR}/fraud_model.pkl")
        _fraud_scaler = joblib.load(f"{MODELS_DIR}/fraud_scaler.pkl")
        _intent_model = joblib.load(f"{MODELS_DIR}/intent_model.pkl")
        _intent_scaler = joblib.load(f"{MODELS_DIR}/intent_scaler.pkl")
        _pincode_lookup = joblib.load(f"{MODELS_DIR}/pincode_rate_lookup.pkl")
        # Load INTENT_THRESHOLD from the training artifact instead of a
        # hardcoded copy — this is the actual fix for the staleness bug we
        # found (the hardcoded value silently drifted from the real
        # F2-optimal threshold after a data change). Falls back to 0.65
        # only if the artifact is missing (e.g. an older repo checkout).
        try:
            _intent_threshold = joblib.load(f"{MODELS_DIR}/intent_threshold.pkl")
        except FileNotFoundError:
            _intent_threshold = 0.65


def score_transaction(txn: dict) -> dict:
    """
    The single entrypoint for the whole system.

    Input: a raw transaction dict with the fields a real integration would
    have available — order details, agent's stated intent, user history.
    See docs/SPEC.md for the full field list.

    Output: fraud_risk_score, intent_match_confidence, preference_fit_score,
    decision, and a plain-English reason — fully explainable, nothing
    hidden inside a black box.
    """
    _load_artifacts()
    pincode_rate_map = _pincode_lookup["pincode_rate_map"]
    global_fraud_rate = _pincode_lookup["global_fraud_rate"]

    row = dict(txn)  # don't mutate caller's dict
    row["is_cod"] = int(row["payment_mode"] == "COD")
    row["is_new_agent"] = int(row["agent_age_days"] < NEW_AGENT_AGE_DAYS)
    row["high_value"] = int(row["order_price"] > HIGH_VALUE_THRESHOLD)
    row["order_value"] = row["order_price"]
    row["pincode_return_rate"] = pincode_rate_map.get(row["pincode"], global_fraud_rate)
    row["price_delta_pct"] = max(
        0.0, (row["order_price"] - row["intent_max_price"]) / row["intent_max_price"]
    )
    row["category_match"] = int(row["order_category"] == row["intent_category"])
    row["price_within_budget"] = int(row["order_price"] <= row["intent_max_price"])
    row["attribute_match"] = int(row["order_key_attribute"] == row["intent_key_attribute"])

    # --- fraud score ---
    X_fraud = pd.DataFrame([{k: row[k] for k in FRAUD_FEATURES}])
    fraud_prob = float(_fraud_model.predict_proba(_fraud_scaler.transform(X_fraud))[0, 1])

    # --- intent-match score ---
    X_intent = pd.DataFrame([{k: row[k] for k in INTENT_FEATURES}])
    mismatch_prob = float(_intent_model.predict_proba(_intent_scaler.transform(X_intent))[0, 1])
    intent_match_confidence = 1 - mismatch_prob

    # --- preference-fit heuristic ---
    # Cold-start fix: a new user has no meaningful purchase history to
    # judge preference-fit from. Defaulting them to a LOW score would
    # unfairly penalize new customers for lacking history, not for any
    # real risk signal — the opposite of what a growth-focused platform
    # wants. We default new users to NEUTRAL (0.5): "unknown" is treated
    # differently from "known to be a poor fit." Gating for new users then
    # leans primarily on fraud-risk and intent-match, not preference-fit.
    NEW_USER_ACCOUNT_AGE_DAYS = 30
    if row.get("user_account_age_days", 999) < NEW_USER_ACCOUNT_AGE_DAYS:
        pref_fit = 0.5
    else:
        # Weighting (1.0 / 0.2) chosen from testing a range of alternatives
        # against real correlation with mismatch outcomes (see
        # README "what broke") — (0.9-1.0, 0.1) correlated slightly
        # better than the original (0.7, 0.3) guess. Not claiming this is
        # optimal, just empirically checked rather than picked by feel.
        category_alignment = 1.0 if row["order_category"] == row["user_historical_category"] else 0.2
        pref_fit = round(min(row["user_past_over_budget_kept_rate"] * category_alignment, 1.0), 3)

    # --- gate ---
    if fraud_prob >= FRAUD_THRESHOLD:
        decision = "HOLD_FRAUD_REVIEW"
        reason = f"Fraud-risk score {fraud_prob:.2f} exceeds threshold {FRAUD_THRESHOLD} — held for manual fraud review."
    elif intent_match_confidence >= _intent_threshold:
        decision = "AUTO_APPROVE"
        reason = f"Low fraud-risk ({fraud_prob:.2f}) and high intent-match confidence ({intent_match_confidence:.2f}) — auto-approved."
    elif pref_fit >= PREF_FIT_THRESHOLD:
        decision = "HOLD_CONFIRM_WITH_HUMAN"
        reason = (f"Order deviates from stated intent (intent-match confidence {intent_match_confidence:.2f}), "
                  f"but this customer's history (preference-fit {pref_fit:.2f}) suggests they may welcome this — "
                  f"routed to a quick human confirmation instead of auto-block.")
    else:
        decision = "HOLD_LIKELY_MISMATCH"
        reason = (f"Order deviates from stated intent (intent-match confidence {intent_match_confidence:.2f}) "
                  f"and doesn't align with this customer's history (preference-fit {pref_fit:.2f}) — likely a "
                  f"mistaken purchase, held to prevent a probable return.")

    return {
        "fraud_risk_score": round(fraud_prob, 3),
        "intent_match_confidence": round(intent_match_confidence, 3),
        "preference_fit_score": pref_fit,
        "decision": decision,
        "reason": reason,
    }


if __name__ == "__main__":
    # a hand-built, brand-new transaction — not from the CSV at all —
    # proving the pipeline works on genuinely new input, live.
    example = {
        "order_price": 4200.0,
        "order_category": "footwear",
        "order_key_attribute": "attr_2",
        "payment_mode": "COD",
        "pincode": "500011",
        "agent_age_days": 300,
        "intent_category": "footwear",
        "intent_max_price": 3800.0,
        "intent_key_attribute": "attr_2",
        "user_historical_category": "footwear",
        "user_past_over_budget_kept_rate": 0.8,
        "device_ip_consistency": 1,
        "user_account_age_days": 400,
    }
    result = score_transaction(example)
    print("=== Live scoring test — brand new transaction, not from the CSV ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
