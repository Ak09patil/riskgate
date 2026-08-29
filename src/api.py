"""
RiskGate local API — exposes score_transaction() over HTTP so the
dashboard's "Run new transaction" button calls the real pipeline live,
instead of replaying pre-computed results from a CSV.

Run with: python3 src/api.py
Then open dashboard/index.html with this server running.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


from flask import Flask, jsonify, request
from flask_cors import CORS
import random
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
    result = score_transaction(txn)
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
        intent = {
            "category": body.get("category", random.choice(_CATEGORIES)),
            "max_price": float(body.get("max_price", random.uniform(1000, 7000))),
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

    return jsonify({
        "status": "SCORED",
        "intent": intent,
        "proposed_product": proposal["matched_product"],
        "matched_rule": proposal["matched_rule"],
        "agent_id": row["agent_id"],
        "order_category": proposal["order_category"],
        "order_price": proposal["order_price"],
        "intent_max_price": intent["max_price"],
        **decision,
    })


if __name__ == "__main__":
    print("RiskGate live API running on http://localhost:5050")
    print("  GET  /simulate   -> scores a random real transaction, live")
    print("  GET  /full_loop  -> shopping agent proposes + RiskGate scores, live")
    print("  POST /score      -> scores a transaction you send in the body")
    app.run(port=5050, debug=False)
