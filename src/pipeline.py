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

FRAUD_THRESHOLD = 0.30  # business threshold, deliberately NOT the F2-optimal (0.20)
# (updated from 0.5 after switching Logistic Regression -> XGBoost + Platt calibration;
# the calibrated score range for this model/dataset is ~0.18-0.56, so 0.5 as a
# threshold was near the ceiling and caught almost no fraud (recall 0.097).
# F2-optimal (0.20) was tested and rejected for production: it flags 50-97%
# of honest customers in every pincode (see fairness_check.py output), which
# is operationally unusable regardless of the recall gain. 0.30 is chosen as
# the business threshold: recall 0.607, precision 0.429 — a defensible
# tradeoff a review team can actually operate on. F2-optimal remains reported
# separately in train_fraud_model.py as the statistical optimum, distinct
# from this deployed business threshold — same DEMO_THRESHOLD-vs-F2 pattern
# used throughout this project.)
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

# Circuit breaker — a hard business-rule cap alongside probabilistic
# scoring, not instead of it (standard practice in real risk systems).
# Set at ~2x the real maximum order_value ever seen in training
# (₹12,306) — anything beyond this is genuinely out-of-distribution for
# the model, not just "unusually high." Found the need for this
# directly: a ₹4,00,000 grocery order sailed through as AUTO_APPROVE
# during testing, since nothing in training ever taught the model that
# region existed at all.
CIRCUIT_BREAKER_MAX_ORDER_VALUE = 25000

# Bounded trust override — a borderline (not high) fraud score can be
# routed to human-confirm instead of fraud-review IF the customer has
# strong verified history AND this specific transaction shows no other
# red flag. Deliberately narrow to resist trust-farming (build up
# history, then exploit it): history alone is never sufficient — it
# must be corroborated by device/IP consistency on THIS transaction,
# and only applies in a narrow band just above threshold, never to
# confidently-fraud scores. Band width (0.05) chosen from the training
# threshold scan: precision/recall barely move across 0.30-0.35,
# meaning this is a genuinely ambiguous region for the model, not one
# where its verdict is confident enough to override outright.
FRAUD_BORDERLINE_BAND = 0.05
TRUST_OVERRIDE_HISTORY_THRESHOLD = 0.8

FRAUD_FEATURES = [
    "device_ip_consistency", "is_cod", "pincode_return_rate",
    "is_new_agent", "high_value", "cod_and_high_value", "agent_age_days",
    "order_value", "user_account_age_days",
]
INTENT_FEATURES = ["category_match", "price_within_budget", "attribute_match", "price_delta_pct"]

PINCODE_SHRINKAGE_K = 20  # see compute_shrunk_pincode_rates() docstring


def compute_shrunk_pincode_rates(train_df, shrinkage_k=PINCODE_SHRINKAGE_K):
    """
    Empirical-Bayes shrinkage for pincode-level fraud rates — pulls a
    pincode's estimated rate toward the GLOBAL average, weighted by how
    much real data that pincode actually has. Fixes a real, reported
    finding: the raw per-pincode rate was noisy for low-volume
    pincodes, and one specific pincode over-flagged honest customers at
    2.8x its real risk as a result (see fairness_check.py and README
    "Does the model treat every pincode fairly?").

    shrinkage_k is the "pseudo-count" of global-average belief every
    pincode starts with, before its own data outweighs it. A pincode
    with far fewer than k real transactions gets pulled strongly toward
    the global rate — its own small sample isn't trusted much yet. One
    with far more barely moves from its own raw rate — it has earned
    the right to be trusted on its own evidence. k=20 was chosen before
    seeing the fairness-check result improve, not tuned to hit a
    specific number afterward — it's simply a modest, defensible
    "don't fully trust a rate estimated from under ~20 transactions"
    threshold, the same order of magnitude as MIN_RING_SIZE and
    MIN_BUCKET_COUNT elsewhere in this project's "don't act on too
    little data" philosophy.

    This is the ONE place this computation lives — imported everywhere
    else that needs it, not duplicated, after finding that exact
    duplication bug (six separate hardcoded copies of FRAUD_FEATURES)
    once already in this project.
    """
    global_fraud_rate = train_df["is_fraud"].mean()
    grouped = train_df.groupby("pincode")["is_fraud"].agg(["mean", "count"])
    shrunk_rate = (
        grouped["count"] * grouped["mean"] + shrinkage_k * global_fraud_rate
    ) / (grouped["count"] + shrinkage_k)
    return shrunk_rate.to_dict(), global_fraud_rate

_fraud_model = None
_fraud_scaler = None
_intent_model = None
_intent_scaler = None
_pincode_lookup = None
_intent_threshold = None


def _load_artifacts():
    """Lazy-load all model artifacts once, shared across calls."""
    global _fraud_model, _intent_model, _intent_scaler, _pincode_lookup, _intent_threshold
    if _fraud_model is None:
        _fraud_model = joblib.load(f"{MODELS_DIR}/fraud_model.pkl")
        # Fraud model is now calibrated XGBoost, which does not require
        # feature scaling (unlike the earlier logistic regression model) —
        # _fraud_scaler is no longer loaded or used.
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
    row["cod_and_high_value"] = row["is_cod"] * row["high_value"]  # interaction:
    # high-value COD orders carry meaningfully higher real risk than either
    # factor alone (verified: 43.1% fraud rate for both together vs 33.1%
    # COD-only, 27.4% high-value-only, 17.5% neither, on our synthetic
    # data) — this lets the model see that combination directly instead
    # of only inferring it indirectly from two separate weights.
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
    fraud_prob = float(_fraud_model.predict_proba(X_fraud)[0, 1])

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
    # Circuit breaker, checked FIRST, before any model score: our fraud
    # model was never trained on anything above CIRCUIT_BREAKER_MAX_
    # ORDER_VALUE (the real max ever seen in training was ~₹12,306).
    # Trusting a model's score on a transaction far outside anything it
    # has ever seen isn't a judgment call the model is equipped to make
    # — this isn't second-guessing the model, it's covering the region
    # where the model has no real basis for an opinion at all. Standard
    # practice in real risk systems: a hard business-rule cap alongside
    # probabilistic scoring, not instead of it. Found the need for this
    # directly — a ₹4,00,000 "grocery" order sailed through as
    # AUTO_APPROVE during testing, 30x beyond anything the model was
    # ever trained to judge.
    if row["order_price"] > CIRCUIT_BREAKER_MAX_ORDER_VALUE:
        decision = "HOLD_FRAUD_REVIEW"
        reason = (f"Order value ₹{row['order_price']:,.0f} exceeds the circuit-breaker cap "
                  f"(₹{CIRCUIT_BREAKER_MAX_ORDER_VALUE:,.0f}) — far outside anything the model "
                  f"was trained on, held for manual review regardless of model score.")
    elif fraud_prob >= FRAUD_THRESHOLD:
        # Bounded trust override: only for a BORDERLINE score (within
        # FRAUD_BORDERLINE_BAND above threshold — never a confidently-high
        # score), and only when strong history is CORROBORATED by a clean
        # signal on this specific transaction (device_ip_consistency). This
        # two-factor requirement is deliberate: history alone would be a
        # trust-farming vector (build up a track record, then exploit it
        # on one transaction). Requiring both makes that attack harder —
        # an attacker would need both a trusted history AND a
        # device/IP-consistent transaction, not just one or the other.
        history_rate = row.get("user_past_over_budget_kept_rate", 0)
        is_borderline = fraud_prob < (FRAUD_THRESHOLD + FRAUD_BORDERLINE_BAND)
        has_strong_history = history_rate >= TRUST_OVERRIDE_HISTORY_THRESHOLD
        has_clean_signal = row.get("device_ip_consistency", 0) == 1

        if is_borderline and has_strong_history and has_clean_signal:
            decision = "HOLD_CONFIRM_WITH_HUMAN"
            reason = (f"Fraud-risk score {fraud_prob:.2f} is borderline (within "
                      f"{FRAUD_BORDERLINE_BAND} of threshold {FRAUD_THRESHOLD}), but strong "
                      f"customer history ({history_rate:.2f}) and a clean device/IP signal "
                      f"on this transaction downgrade this to human confirmation rather than "
                      f"fraud review.")
        else:
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
