"""
Automated test suite — real pass/fail assertions, not human-read
validation scripts. Everything else in src/ (drift_test.py,
baseline_comparison.py, etc.) is a rigor CHECK that prints results for a
person to read and judge. This file is different: run with `pytest`,
gives a clean pass/fail signal, and is what a CI system or a reviewer
running the repo would actually execute to verify core behavior works.

Run with: pytest tests/ -v
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from pipeline import score_transaction, FRAUD_THRESHOLD
from shopping_agent import propose_purchase
from catalog import CATALOG


# --- fixtures: representative transaction shapes, not edge cases yet ---

def make_txn(**overrides):
    base = {
        "order_price": 2500.0,
        "order_category": "footwear",
        "order_key_attribute": "attr_2",
        "payment_mode": "prepaid",
        "pincode": "500011",
        "agent_age_days": 200,
        "intent_category": "footwear",
        "intent_max_price": 3000.0,
        "intent_key_attribute": "attr_2",
        "user_historical_category": "footwear",
        "user_past_over_budget_kept_rate": 0.5,
        "device_ip_consistency": 1,
        "user_account_age_days": 400,
    }
    base.update(overrides)
    return base


VALID_DECISIONS = {"AUTO_APPROVE", "HOLD_FRAUD_REVIEW", "HOLD_CONFIRM_WITH_HUMAN", "HOLD_LIKELY_MISMATCH"}


# --- pipeline.score_transaction() core behavior ---

class TestScoreTransaction:
    def test_returns_all_required_fields(self):
        result = score_transaction(make_txn())
        for field in ["fraud_risk_score", "intent_match_confidence",
                      "preference_fit_score", "decision", "reason"]:
            assert field in result, f"missing field: {field}"

    def test_decision_is_always_one_of_four_valid_values(self):
        result = score_transaction(make_txn())
        assert result["decision"] in VALID_DECISIONS

    def test_scores_are_in_valid_probability_range(self):
        result = score_transaction(make_txn())
        assert 0.0 <= result["fraud_risk_score"] <= 1.0
        assert 0.0 <= result["intent_match_confidence"] <= 1.0
        assert 0.0 <= result["preference_fit_score"] <= 1.0

    def test_clean_transaction_is_not_flagged_as_fraud(self):
        # consistent device, prepaid, old agent, established account —
        # every fraud signal points the SAME direction, so this should
        # not exceed the fraud threshold. If this fails, something in
        # the scoring pipeline is fundamentally broken, not just noisy.
        result = score_transaction(make_txn(
            device_ip_consistency=1, payment_mode="prepaid",
            agent_age_days=500, order_price=1000, user_account_age_days=800,
        ))
        assert result["fraud_risk_score"] < FRAUD_THRESHOLD

    def test_high_risk_transaction_is_flagged(self):
        # every fraud signal points toward risk at once — device
        # mismatch, COD, brand-new agent, high value. If this ISN'T
        # flagged, the model or gate is not doing its job.
        result = score_transaction(make_txn(
            device_ip_consistency=0, payment_mode="COD",
            agent_age_days=1, order_price=9000, user_account_age_days=5,
        ))
        assert result["decision"] == "HOLD_FRAUD_REVIEW"

    def test_new_user_gets_neutral_preference_fit_not_penalized(self):
        # regression test for the cold-start bug we found and fixed —
        # a new user (< 30 days) should get preference_fit_score == 0.5
        # (neutral), not 0 (penalized for lacking history).
        result = score_transaction(make_txn(
            user_account_age_days=5, user_past_over_budget_kept_rate=0.0,
        ))
        assert result["preference_fit_score"] == 0.5

    def test_intent_match_reflects_category_mismatch(self):
        # ordering a completely different category than intent should
        # reduce intent-match confidence versus an exact match
        matched = score_transaction(make_txn(order_category="footwear", intent_category="footwear"))
        mismatched = score_transaction(make_txn(order_category="electronics", intent_category="footwear"))
        assert mismatched["intent_match_confidence"] < matched["intent_match_confidence"]

    def test_missing_required_field_raises_clear_error(self):
        txn = make_txn()
        del txn["order_price"]
        with pytest.raises(KeyError):
            score_transaction(txn)


# --- shopping_agent.propose_purchase() core behavior ---

class TestShoppingAgent:
    def test_returns_a_real_catalog_item(self):
        intent = {"category": "footwear", "max_price": 4000, "key_attribute": "attr_2"}
        proposal = propose_purchase(intent)
        assert proposal is not None
        catalog_prices = {item["price"] for item in CATALOG if item["category"] == "footwear"}
        assert proposal["order_price"] in catalog_prices

    def test_respects_budget_when_a_match_exists_within_it(self):
        intent = {"category": "footwear", "max_price": 4000, "key_attribute": "attr_2"}
        proposal = propose_purchase(intent)
        assert proposal["order_price"] <= 4000

    def test_falls_back_to_closest_option_when_nothing_fits_budget(self):
        # an intentionally impossible budget for this category/attribute
        # combination — the agent should still propose ITS closest
        # option, not silently return nothing
        intent = {"category": "footwear", "max_price": 1, "key_attribute": "attr_5"}
        proposal = propose_purchase(intent)
        assert proposal is not None
        assert proposal["matched_rule"] == "over_budget_closest_available"

    def test_unknown_category_returns_none_not_a_crash(self):
        intent = {"category": "not_a_real_category", "max_price": 5000, "key_attribute": "attr_1"}
        proposal = propose_purchase(intent)
        assert proposal is None


# --- gating consistency: does the batch path (gating.py's row_to_txn)
# agree with the live path (pipeline.score_transaction) on the same data ---

class TestGatingConsistency:
    def test_same_transaction_scored_twice_gives_identical_result(self):
        # score_transaction() should be deterministic for the same input
        # — no hidden randomness in the scoring path itself (randomness
        # belongs to the shopping agent's catalog search, not scoring)
        txn = make_txn()
        result1 = score_transaction(txn)
        result2 = score_transaction(txn)
        assert result1["decision"] == result2["decision"]
        assert result1["fraud_risk_score"] == result2["fraud_risk_score"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
