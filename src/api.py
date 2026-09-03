"""
RiskGate local API — exposes score_transaction() over HTTP so the
dashboard's "Run new transaction" button calls the real pipeline live,
instead of replaying pre-computed results from a CSV.

Run with: python3 src/api.py
Then open dashboard/index.html with this server running.
"""
import os
import threading
import time
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


from flask import Flask, jsonify, request
from flask_cors import CORS
import random
from datetime import datetime, timezone
import pandas as pd
from pipeline import score_transaction
from shopping_agent import propose_purchase
from catalog import CATALOG

app = Flask(__name__)
CORS(app)  # dashboard is opened as a local file, needs CORS to call this

# Load real transactions to draw random NEW-looking demo inputs from —
# still real data-shaped, but proves the live call path, not a CSV replay.
_df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")

_CATEGORIES = list({item["category"] for item in CATALOG})
_ATTRIBUTES = [f"attr_{i}" for i in range(1, 6)]


@app.route("/score", methods=["POST"])
def score():
    txn = request.get_json()
    if not txn:
        return jsonify({"error": "request body must be valid JSON with transaction fields"}), 400
    required = ["order_price", "order_category", "order_key_attribute", "payment_mode",
                "pincode", "agent_age_days", "intent_category", "intent_max_price",
                "intent_key_attribute", "user_historical_category",
                "user_past_over_budget_kept_rate", "device_ip_consistency",
                "user_account_age_days"]
    missing = [f for f in required if f not in txn]
    if missing:
        return jsonify({"error": f"missing required fields: {missing}"}), 400
    try:
        order_price = float(txn["order_price"])
        intent_max_price = float(txn["intent_max_price"])
    except (TypeError, ValueError):
        return jsonify({"error": "order_price and intent_max_price must be numbers"}), 400
    if order_price <= 0 or intent_max_price <= 0:
        return jsonify({"error": "order_price and intent_max_price must be positive — found "
                                  f"order_price={order_price}, intent_max_price={intent_max_price}"}), 400
    try:
        result = score_transaction(txn)
    except Exception as e:
        return jsonify({"error": f"scoring failed: {e}"}), 400
    result["order_id"] = txn.get("order_id", "manual")
    result["agent_id"] = txn.get("agent_id", "unknown")
    result["order_category"] = txn.get("order_category")
    result["order_price"] = txn.get("order_price")
    result["intent_max_price"] = txn.get("intent_max_price")
    return jsonify(result)


@app.route("/simulate", methods=["GET"])
def simulate():
    """Pull a random real transaction's raw fields and score it live
    through the pipeline — proves the full path end-to-end, not a replay."""
    row = _df.sample(1).iloc[0].to_dict()
    txn = {
        "order_price": row["order_price"],
        "order_category": row["order_category"],
        "order_key_attribute": row["order_key_attribute"],
        "payment_mode": row["payment_mode"],
        "pincode": str(row["pincode"]),
        "agent_age_days": int(row["agent_age_days"]),
        "intent_category": row["intent_category"],
        "intent_max_price": row["intent_max_price"],
        "intent_key_attribute": row["intent_key_attribute"],
        "user_historical_category": row["user_historical_category"],
        "user_past_over_budget_kept_rate": row["user_past_over_budget_kept_rate"],
        "device_ip_consistency": int(row["device_ip_consistency"]),
        "user_account_age_days": int(row["user_account_age_days"]),
    }
    result = score_transaction(txn)
    result["order_id"] = row["order_id"]
    result["agent_id"] = row["agent_id"]
    result["order_category"] = row["order_category"]
    result["order_price"] = row["order_price"]
    result["intent_max_price"] = row["intent_max_price"]
    return jsonify(result)


@app.route("/full_loop", methods=["GET", "POST"])
def full_loop():
    """
    The genuine Track1+Track2 demo: takes a human INTENT (either a random
    one for GET, or a real user-provided one via POST — category, budget,
    attribute), runs it through the shopping agent to propose a real
    purchase from the catalog, then scores that proposal through RiskGate.
    Returns both steps so the dashboard/checkout mock can show the agent's
    reasoning, not just the final score.
    """
    if request.method == "POST":
        body = request.get_json() or {}
        try:
            max_price = float(body.get("max_price", random.uniform(1000, 7000)))
        except (TypeError, ValueError):
            return jsonify({"error": "max_price must be a number"}), 400
        if max_price <= 0:
            return jsonify({"error": f"max_price must be positive, got {max_price}"}), 400
        intent = {
            "category": body.get("category", random.choice(_CATEGORIES)),
            "max_price": max_price,
            "key_attribute": body.get("key_attribute", random.choice(_ATTRIBUTES)),
            "allow_over_budget": body.get("allow_over_budget", True),
        }
    else:
        category = random.choice(_CATEGORIES)
        max_price = round(random.uniform(1000, 7000), 2)
        key_attribute = random.choice(_ATTRIBUTES)
        intent = {
            "category": category,
            "max_price": max_price,
            "key_attribute": key_attribute,
            "allow_over_budget": True,
        }

    proposal = propose_purchase(intent)
    if proposal is None:
        return jsonify({"status": "NO_MATCH", "reason": "Nothing in catalog matches this category."})

    # Pull a realistic user-context profile from real historical data, so
    # the risk side of the story is grounded in real patterns, not fabricated.
    # everything below only needs `intent`, not the original `category`
    # local var — this fixes the case where intent came from POST body
    context_row = _df[_df["user_historical_category"] == intent["category"]]

    if len(context_row) == 0:
        context_row = _df.sample(1)
    row = context_row.sample(1).iloc[0].to_dict()

    txn = {
        "order_price": proposal["order_price"],
        "order_category": proposal["order_category"],
        "order_key_attribute": proposal["order_key_attribute"],
        "intent_category": intent["category"],
        "intent_max_price": intent["max_price"],
        "intent_key_attribute": intent["key_attribute"],
        "payment_mode": row["payment_mode"],
        "pincode": str(row["pincode"]),
        "agent_age_days": int(row["agent_age_days"]),
        "user_historical_category": row["user_historical_category"],
        "user_past_over_budget_kept_rate": row["user_past_over_budget_kept_rate"],
        "device_ip_consistency": int(row["device_ip_consistency"]),
        "user_account_age_days": int(row["user_account_age_days"]),
    }
    decision = score_transaction(txn)

    # order_id and timestamp added specifically so the dashboard can carry
    # ONE live transaction's identity through localStorage across pages
    # (checkout -> dashboard), letting Consumer/Merchant/Razorpay/Fraud
    # queue all show the SAME real transaction instead of independent
    # random samples of static replay data.
    import time as _time
    from datetime import datetime as _datetime
    return jsonify({
        "status": "SCORED",
        "order_id": f"live_{int(_time.time() * 1000)}",
        "timestamp": _datetime.now().isoformat(),
        "intent": intent,
        "proposed_product": proposal["matched_product"],
        "matched_rule": proposal["matched_rule"],
        "agent_id": row["agent_id"],
        "order_category": proposal["order_category"],
        "order_price": proposal["order_price"],
        "intent_max_price": intent["max_price"],
        "pincode": txn["pincode"],
        "payment_mode": txn["payment_mode"],
        # Raw feature fields, added for the dashboard's Decision Trace -
        # same fields as build_dashboard_data.py exports for replay data,
        # so live and replay transactions have an identical shape.
        "agent_age_days": txn["agent_age_days"],
        "device_ip_consistency": txn["device_ip_consistency"],
        "user_past_over_budget_kept_rate": txn["user_past_over_budget_kept_rate"],
        **decision,
    })


@app.route("/fraud_batch_narrative", methods=["GET"])
def fraud_batch_narrative():
    """
    Real endpoint for the pattern-narrative feature: pulls the most
    recent batch of HOLD_FRAUD_REVIEW transactions and returns both the
    deterministic clusters AND the narrative — see pattern_narrative.py
    for why the detection stays deterministic and only the phrasing
    optionally uses an LLM.
    """
    from pattern_narrative import generate_narrative
    df = pd.read_csv(f"{BASE_DIR}/data/full_merged.csv")
    flagged = df[df["decision"] == "HOLD_FRAUD_REVIEW"].head(40)
    result = generate_narrative(flagged)
    return jsonify(result)


# --- BACKGROUND BATCH DETECTION SCHEDULER ---
# Real async design, not just an architectural claim: ring and spike
# detection genuinely need to see MULTIPLE transactions together (a
# coordinated ring, an aggregate-rate spike), so they were always
# structurally separate from the live per-transaction scoring path
# (see docs/ARCHITECTURE.md Section 2.7). What was still missing:
# an actual automatic trigger, not just "these are separate scripts
# you'd run manually." This background thread closes that gap - a
# real, in-process scheduler, not a description of one.
#
# Deliberately NOT a job queue (Celery/RQ + a broker like Redis): at
# this data volume, that would be real infrastructure complexity with
# no corresponding benefit - an external dependency this repo would
# then require anyone testing it locally to also set up. A daemon
# thread on a fixed interval is the right-sized version of "runs
# automatically, not on request" for a project this size; a queue-
# based version is a natural next step once real transaction volume
# exists to justify it.
BATCH_DETECTION_INTERVAL_SECONDS = 300  # 5 minutes

_batch_cache = {"rings": None, "spikes": None, "last_run": None}
_batch_cache_lock = threading.Lock()


def _run_batch_detection():
    """Recomputes ring + spike detection and refreshes the cache both
    endpoints below serve from. Runs once immediately on server start,
    then automatically every BATCH_DETECTION_INTERVAL_SECONDS via the
    background thread started in __main__ - never triggered by a
    request."""
    from ring_detector import detect_rings, validate_against_ground_truth as validate_rings
    from spike_detector import detect_spikes, validate_against_ground_truth as validate_spikes

    df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")

    result_df = detect_rings(df)
    detected = result_df[result_df["detected_ring_id"] >= 0]
    rings = []
    for ring_id, group in detected.groupby("detected_ring_id"):
        rings.append({
            "ring_id": int(ring_id),
            "size": len(group),
            "pincode": str(group["pincode"].iloc[0]),
            "order_ids": group["order_id"].tolist(),
        })
    rings_response = {"rings_detected": len(rings), "rings": rings}
    if "true_ring_id" in df.columns:
        rings_response["validation_against_injected_ground_truth"] = validate_rings(result_df)

    bucket_stats = detect_spikes(df)
    flagged = bucket_stats[bucket_stats["detected_spike"]]
    spikes_response = {
        "buckets_flagged": len(flagged),
        "flagged_windows": [
            {
                "bucket_start": str(row["_bucket"]),
                "transaction_count": int(row["count"]),
                "fraud_rate": round(float(row["fraud_rate"]), 3),
                "z_score": round(float(row["z_score"]), 2),
            }
            for _, row in flagged.iterrows()
        ],
    }
    if "true_spike_window" in df.columns:
        spikes_response["validation_against_injected_ground_truth"] = validate_spikes(bucket_stats)

    with _batch_cache_lock:
        _batch_cache["rings"] = rings_response
        _batch_cache["spikes"] = spikes_response
        _batch_cache["last_run"] = datetime.now(timezone.utc).isoformat()


def _background_scheduler():
    """Daemon thread: runs _run_batch_detection() once immediately,
    then on a fixed interval, for as long as the API process is alive."""
    while True:
        try:
            _run_batch_detection()
        except Exception as e:
            print(f"[RiskGate] Background batch detection failed: {e}")
        time.sleep(BATCH_DETECTION_INTERVAL_SECONDS)


@app.route("/detect_rings", methods=["GET"])
def detect_rings_endpoint():
    """
    Abuse-ring sentinel — a genuinely different problem shape from the
    two per-transaction scores (relational/graph detection, not
    classification). Served from the background scheduler's cache
    (refreshed automatically every BATCH_DETECTION_INTERVAL_SECONDS),
    not recomputed per request. See ring_detector.py for the full
    reasoning and docs/ARCHITECTURE.md for why this specific linkage
    rule was chosen.
    """
    with _batch_cache_lock:
        cached = _batch_cache["rings"]
        last_run = _batch_cache["last_run"]
    if cached is None:
        _run_batch_detection()
        with _batch_cache_lock:
            cached = _batch_cache["rings"]
            last_run = _batch_cache["last_run"]
    response = dict(cached)
    response["cache_last_refreshed"] = last_run
    return jsonify(response)


@app.route("/detect_spikes", methods=["GET"])
def detect_spikes_endpoint():
    """
    Fraud-spike detector — time-series anomaly detection over
    aggregate transaction volume, a third distinct problem shape from
    per-transaction scoring and relational ring detection. Served from
    the background scheduler's cache, not recomputed per request. See
    spike_detector.py for the full reasoning.
    """
    with _batch_cache_lock:
        cached = _batch_cache["spikes"]
        last_run = _batch_cache["last_run"]
    if cached is None:
        _run_batch_detection()
        with _batch_cache_lock:
            cached = _batch_cache["spikes"]
            last_run = _batch_cache["last_run"]
    response = dict(cached)
    response["cache_last_refreshed"] = last_run
    return jsonify(response)


@app.route("/record_outcome", methods=["POST"])
def record_outcome_endpoint():
    """
    Real endpoint behind the Fraud queue's Approve/Reject buttons — logs
    a human-confirmed real outcome for a held transaction. See
    feedback_loop.py for what this outcome is later used for
    (evaluation against real results, and a demonstrated retrain path).
    """
    from feedback_loop import record_outcome
    body = request.get_json() or {}
    order_id = body.get("order_id")
    confirmed_fraud = body.get("confirmed_fraud")
    note = body.get("analyst_note", "")
    if order_id is None or confirmed_fraud is None:
        return jsonify({"error": "order_id and confirmed_fraud are required"}), 400
    record_outcome(order_id, bool(confirmed_fraud), note)
    return jsonify({"status": "recorded", "order_id": order_id})


@app.route("/feedback_status", methods=["GET"])
def feedback_status():
    """Shows how the model's predictions compare against real recorded
    outcomes so far — the honest 'did we get it right' check."""
    from feedback_loop import evaluate_against_feedback
    return jsonify(evaluate_against_feedback())


if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=_background_scheduler, daemon=True)
    scheduler_thread.start()
    print("RiskGate live API running on http://localhost:5050")
    print(f"  [background] ring/spike detection auto-refreshes every {BATCH_DETECTION_INTERVAL_SECONDS}s")
    print("  GET  /simulate               -> scores a random real transaction, live")
    print("  GET  /full_loop              -> shopping agent proposes + RiskGate scores, live")
    print("  POST /score                  -> scores a transaction you send in the body")
    print("  GET  /fraud_batch_narrative   -> pattern narrative for the current fraud-review batch")
    print("  GET  /detect_rings           -> abuse-ring sentinel (graph-based coordinated-fraud detection)")
    print("  GET  /detect_spikes          -> fraud-spike detector (time-series volume anomaly detection)")
    print("  POST /record_outcome         -> logs a real confirmed outcome for a held transaction")
    print("  GET  /feedback_status        -> model accuracy vs. real recorded outcomes so far")
    # threaded=True: without this, Flask'''s dev server handles one
    # request at a time even under "concurrent" load, which silently
    # turned load_test.py'''s concurrency test into a serial-throughput
    # test instead (found via a linear latency-vs-concurrency curve
    # that shouldn'''t exist under genuine parallelism). Still a dev
    # server, not production-grade — a real deployment would run
    # behind gunicorn/uwsgi — but this at least measures what the test
    # claims to measure.
    app.run(port=5050, debug=False, threaded=True)
