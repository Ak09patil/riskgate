"""
Full end-to-end loop: human intent -> shopping agent proposes a purchase
-> RiskGate scores and gates it -> decision.

This is Track 1 + Track 2, genuinely connected, not described separately.
The shopping agent's output plugs directly into score_transaction() with
only the fields RiskGate needs (fraud/history context) filled in from a
simulated user profile.
"""

from shopping_agent import propose_purchase
from pipeline import score_transaction


def run_full_loop(intent: dict, user_context: dict) -> dict:
    """
    intent: what the human told the agent to do (category, max_price, key_attribute)
    user_context: history/fraud-relevant fields RiskGate needs, that a real
    integration would already have on file (device consistency, past
    behavior, agent age, etc.) — the shopping agent doesn't need or see
    these; only RiskGate does. This separation matters: the agent that
    proposes a purchase and the layer that risk-checks it don't share
    context beyond the proposed order itself, same as a real merchant
    wouldn't hand its fraud signals to a third-party shopping assistant.
    """
    proposal = propose_purchase(intent)
    if proposal is None:
        return {"status": "NO_MATCH", "reason": "Nothing in catalog matches this category."}

    txn = {
        "order_price": proposal["order_price"],
        "order_category": proposal["order_category"],
        "order_key_attribute": proposal["order_key_attribute"],
        "intent_category": intent["category"],
        "intent_max_price": intent["max_price"],
        "intent_key_attribute": intent["key_attribute"],
        **user_context,
    }
    decision = score_transaction(txn)
    return {
        "status": "SCORED",
        "proposed_product": proposal["matched_product"],
        "matched_rule": proposal["matched_rule"],
        **decision,
    }


if __name__ == "__main__":
    print("=== FULL LOOP — Case A: clean match, established user ===")
    result = run_full_loop(
        intent={"category": "footwear", "max_price": 4000, "key_attribute": "attr_2"},
        user_context={
            "payment_mode": "prepaid",
            "pincode": "500011",
            "agent_age_days": 300,
            "user_historical_category": "footwear",
            "user_past_over_budget_kept_rate": 0.4,
            "device_ip_consistency": 1,
            "user_account_age_days": 400,
        },
    )
    for k, v in result.items():
        print(f"  {k}: {v}")

    print("\n=== FULL LOOP — Case B: forced over-budget, but user has history of keeping such orders ===")
    result = run_full_loop(
        intent={"category": "footwear", "max_price": 1500, "key_attribute": "attr_5"},
        user_context={
            "payment_mode": "prepaid",
            "pincode": "500011",
            "agent_age_days": 300,
            "user_historical_category": "footwear",
            "user_past_over_budget_kept_rate": 0.85,  # high — likely to welcome the deviation
            "device_ip_consistency": 1,
            "user_account_age_days": 400,
        },
    )
    for k, v in result.items():
        print(f"  {k}: {v}")

    print("\n=== FULL LOOP — Case C: suspicious context — new agent, COD, risky pincode ===")
    result = run_full_loop(
        intent={"category": "electronics", "max_price": 5000, "key_attribute": "attr_3"},
        user_context={
            "payment_mode": "COD",
            "pincode": "500020",
            "agent_age_days": 3,        # brand new agent
            "user_historical_category": "electronics",
            "user_past_over_budget_kept_rate": 0.2,
            "device_ip_consistency": 0,  # mismatch
            "user_account_age_days": 15,
        },
    )
    for k, v in result.items():
        print(f"  {k}: {v}")
