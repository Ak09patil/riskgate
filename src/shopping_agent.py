"""
Shopping agent — the Track 1 half of the system.

Its ONE job: given a human's stated intent (category, budget, preferred
attribute), propose a purchase from the catalog. Deliberately rule-based,
not LLM-driven — bounded, debuggable, and fast, matching the same
discipline used everywhere else in this system.

This does NOT decide whether the proposed purchase is safe or a good idea
— that's RiskGate's job entirely. The agent proposes; RiskGate disposes.
Output is shaped to plug directly into pipeline.score_transaction() with
no translation needed.
"""

from catalog import CATALOG


def propose_purchase(intent: dict) -> dict:
    """
    intent: {
        "category": str,
        "max_price": float,
        "key_attribute": str,       # preferred attribute, e.g. "attr_2"
        "allow_over_budget": bool,  # if True, may surface a close over-budget option
    }

    Returns a proposed order dict shaped for pipeline.score_transaction(),
    or None if nothing in the category exists at all.

    Raises ValueError for a non-positive max_price — this is validated
    HERE, not just at the API layer, because a negative or zero budget
    silently proceeding would otherwise produce a nonsensical proposal
    (found via direct-call testing: a -500 budget was treated as "over
    budget" and matched to a real, positive-priced product, which is
    wrong, not just unvalidated).
    """
    category = intent["category"]
    max_price = intent["max_price"]
    key_attribute = intent["key_attribute"]
    allow_over_budget = intent.get("allow_over_budget", True)

    if max_price is None or max_price <= 0:
        raise ValueError(f"max_price must be positive, got {max_price}")

    candidates = [item for item in CATALOG if item["category"] == category]
    if not candidates:
        return None

    # --- rule 1: exact attribute match, within budget, cheapest such option ---
    in_budget_attr_match = [
        c for c in candidates if c["attribute"] == key_attribute and c["price"] <= max_price
    ]
    if in_budget_attr_match:
        chosen = min(in_budget_attr_match, key=lambda c: c["price"])
        return _to_order(chosen, matched_rule="exact_attribute_in_budget")

    # --- rule 2: any category match, within budget, cheapest ---
    in_budget_any = [c for c in candidates if c["price"] <= max_price]
    if in_budget_any:
        chosen = min(in_budget_any, key=lambda c: c["price"])
        return _to_order(chosen, matched_rule="category_in_budget_attribute_mismatch")

    # --- rule 3: nothing in budget — surface the closest over-budget option,
    # only if the intent allows it. This is the case that feeds RiskGate's
    # preference-fit path: a deviation the agent is proposing because it's
    # the best available fit, not a mistake. ---
    if allow_over_budget:
        closest_over = min(candidates, key=lambda c: c["price"])
        return _to_order(closest_over, matched_rule="over_budget_closest_available")

    return None


def _to_order(item: dict, matched_rule: str) -> dict:
    return {
        "order_price": float(item["price"]),
        "order_category": item["category"],
        "order_key_attribute": item["attribute"],
        "matched_product": item["name"],
        "matched_rule": matched_rule,
    }


if __name__ == "__main__":
    # a clean in-budget case
    print("=== Case 1: clean in-budget match ===")
    result = propose_purchase({
        "category": "footwear", "max_price": 4000, "key_attribute": "attr_2",
    })
    print(result)

    # a case where nothing fits budget/attribute, forcing an over-budget proposal
    print("\n=== Case 2: forced over-budget proposal ===")
    result = propose_purchase({
        "category": "footwear", "max_price": 1500, "key_attribute": "attr_5",
    })
    print(result)
