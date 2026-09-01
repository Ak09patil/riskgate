import sys

path = sys.argv[1] if len(sys.argv) > 1 else "tests/test_integration.py"

with open(path, "r") as f:
    content = f.read()

old_docstring = '''    def test_over_budget_proposal_with_good_history_routes_to_confirm(self):
        """Regression test for the exact scenario we designed the
        three-score architecture around: an agent proposes something
        over budget, but the user's history suggests they'd welcome it
        — this MUST route to HOLD_CONFIRM_WITH_HUMAN, not silently
        auto-approve or block. If this breaks, the core thesis breaks."""'''

new_docstring = '''    def test_over_budget_proposal_with_good_history_routes_to_confirm(self):
        """Regression test for the exact scenario we designed the
        three-score architecture around: an agent proposes something
        over budget, but the user's history suggests they'd welcome it
        — this MUST route to HOLD_CONFIRM_WITH_HUMAN, not silently
        auto-approve or block. If this breaks, the core thesis breaks.

        NOTE (post XGBoost switch): this specific scenario's fraud score
        (~0.31) now lands in the fraud-borderline band, so this passes
        via the bounded trust override (see
        TestBoundedTrustOverride below) rather than the original
        intent-mismatch + preference-fit path it was originally written
        to test. The outcome checked here is still correct and still
        matters, but see TestBoundedTrustOverride for direct coverage
        of THAT mechanism specifically."""'''

if old_docstring not in content:
    print("PATTERN NOT FOUND - docstring")
    sys.exit(1)

content = content.replace(old_docstring, new_docstring)

# Insert new test class right after TestFullLoopIntegration's last method,
# before the "# --- Live API integration" comment block.
anchor = "# --- Live API integration: real Flask routes, via Flask's test client"

new_tests = '''class TestBoundedTrustOverride:
    """Direct coverage of the bounded trust override added to
    pipeline.py's gating logic after the XGBoost switch (previously
    only verified manually in a chat session, not in the test suite —
    see git history). Two-factor by design: strong history alone must
    NOT be sufficient (that would be a trust-farming vector — build up
    a track record, then exploit it on one bad transaction), and the
    override must only ever apply to a genuinely borderline score, not
    a confidently-high one."""

    def _make_txn(self, agent_age_days, device_ip_consistency,
                   user_past_over_budget_kept_rate, order_price=1000):
        return {
            "order_price": order_price, "order_value": order_price,
            "order_category": "footwear", "order_key_attribute": "attr_2",
            "intent_category": "footwear", "intent_max_price": 1500,
            "intent_key_attribute": "attr_2",
            "payment_mode": "prepaid", "pincode": "500011",
            "agent_age_days": agent_age_days,
            "user_historical_category": "footwear",
            "user_past_over_budget_kept_rate": user_past_over_budget_kept_rate,
            "device_ip_consistency": device_ip_consistency,
            "user_account_age_days": 400,
        }

    def test_borderline_score_with_strong_history_and_clean_signal_gets_override(self):
        """The happy path: borderline fraud score + strong history +
        clean device/IP signal on THIS transaction -> override applies,
        routes to human-confirm instead of fraud-review."""
        from pipeline import score_transaction
        txn = self._make_txn(agent_age_days=150, device_ip_consistency=1,
                              user_past_over_budget_kept_rate=0.9)
        result = score_transaction(txn)
        assert 0.30 <= result["fraud_risk_score"] < 0.35, (
            f"Test fixture assumption broken: expected a borderline score "
            f"in [0.30, 0.35), got {result['fraud_risk_score']} — this test "
            f"needs its agent_age_days recalibrated if the model changed."
        )
        assert result["decision"] == "HOLD_CONFIRM_WITH_HUMAN"

    def test_borderline_score_with_strong_history_but_dirty_signal_does_NOT_get_override(self):
        """The trust-farming defense: strong history alone, WITHOUT a
        clean device/IP signal on this specific transaction, must NOT
        be enough to earn the override. This is the two-factor
        requirement's whole reason for existing — verified here with a
        score confirmed to still land in the borderline band."""
        from pipeline import score_transaction
        txn = self._make_txn(agent_age_days=150, device_ip_consistency=0,
                              user_past_over_budget_kept_rate=0.9)
        result = score_transaction(txn)
        assert 0.30 <= result["fraud_risk_score"] < 0.35, (
            f"Test fixture assumption broken: expected a borderline score "
            f"in [0.30, 0.35), got {result['fraud_risk_score']} — this test "
            f"needs recalibrating if the model changed."
        )
        assert result["decision"] == "HOLD_FRAUD_REVIEW"

    def test_high_fraud_score_never_gets_override_regardless_of_history(self):
        """The override must be bounded to a narrow borderline band —
        it must NEVER apply to a confidently-high fraud score, no
        matter how strong the history. This is what keeps the override
        from becoming a general history-overrides-fraud escape hatch."""
        from pipeline import score_transaction
        txn = self._make_txn(agent_age_days=50, device_ip_consistency=1,
                              user_past_over_budget_kept_rate=1.0)
        result = score_transaction(txn)
        assert result["fraud_risk_score"] >= 0.35, (
            f"Test fixture assumption broken: expected a confidently-high "
            f"score >= 0.35, got {result['fraud_risk_score']} — this test "
            f"needs recalibrating if the model changed."
        )
        assert result["decision"] == "HOLD_FRAUD_REVIEW"


''' + anchor

if anchor not in content:
    print("PATTERN NOT FOUND - anchor")
    sys.exit(1)

content = content.replace(anchor, new_tests)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
