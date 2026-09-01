import sys

path = sys.argv[1] if len(sys.argv) > 1 else "tests/test_integration.py"

with open(path, "r") as f:
    content = f.read()

old_class = '''class TestBoundedTrustOverride:
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
        assert result["decision"] == "HOLD_FRAUD_REVIEW"'''

new_class = '''class TestBoundedTrustOverride:
    """Direct coverage of the bounded trust override added to
    pipeline.py's gating logic after the XGBoost switch (previously
    only verified manually in a chat session, not in the test suite —
    see git history). Two-factor by design: strong history alone must
    NOT be sufficient (that would be a trust-farming vector - build up
    a track record, then exploit it on one bad transaction), and the
    override must only ever apply to a genuinely borderline score, not
    a confidently-high one.

    Fixture values below were found by scanning the live model's
    actual score output for each scenario (not assumed/estimated), then
    locked in as regression values. Each assertion re-checks the score
    lands in the expected band before checking the decision, so that if
    a future retrain shifts the model's score distribution, this fails
    with a clear "fixture needs recalibrating" message rather than a
    confusing decision mismatch."""

    def _make_txn(self, agent_age_days, device_ip_consistency,
                   user_past_over_budget_kept_rate, order_price,
                   payment_mode, user_account_age_days):
        return {
            "order_price": order_price, "order_value": order_price,
            "order_category": "footwear", "order_key_attribute": "attr_2",
            "intent_category": "footwear", "intent_max_price": 6000,
            "intent_key_attribute": "attr_2",
            "payment_mode": payment_mode, "pincode": "500011",
            "agent_age_days": agent_age_days,
            "user_historical_category": "footwear",
            "user_past_over_budget_kept_rate": user_past_over_budget_kept_rate,
            "device_ip_consistency": device_ip_consistency,
            "user_account_age_days": user_account_age_days,
        }

    def test_borderline_score_with_strong_history_and_clean_signal_gets_override(self):
        """The happy path: borderline fraud score + strong history +
        clean device/IP signal on THIS transaction -> override applies,
        routes to human-confirm instead of fraud-review."""
        from pipeline import score_transaction
        txn = self._make_txn(agent_age_days=150, device_ip_consistency=1,
                              user_past_over_budget_kept_rate=0.9,
                              order_price=7000, payment_mode="COD",
                              user_account_age_days=400)
        result = score_transaction(txn)
        assert 0.30 <= result["fraud_risk_score"] < 0.35, (
            f"Test fixture assumption broken: expected a borderline score "
            f"in [0.30, 0.35), got {result['fraud_risk_score']} — this test "
            f"needs recalibrating if the model changed."
        )
        assert result["decision"] == "HOLD_CONFIRM_WITH_HUMAN"

    def test_borderline_score_with_strong_history_but_dirty_signal_does_NOT_get_override(self):
        """The trust-farming defense: strong history alone, WITHOUT a
        clean device/IP signal on this specific transaction, must NOT
        be enough to earn the override. This is the two-factor
        requirement's whole reason for existing - verified here with a
        score confirmed to still land in the borderline band."""
        from pipeline import score_transaction
        txn = self._make_txn(agent_age_days=100, device_ip_consistency=0,
                              user_past_over_budget_kept_rate=0.9,
                              order_price=3000, payment_mode="prepaid",
                              user_account_age_days=400)
        result = score_transaction(txn)
        assert 0.30 <= result["fraud_risk_score"] < 0.35, (
            f"Test fixture assumption broken: expected a borderline score "
            f"in [0.30, 0.35), got {result['fraud_risk_score']} — this test "
            f"needs recalibrating if the model changed."
        )
        assert result["decision"] == "HOLD_FRAUD_REVIEW"

    def test_high_fraud_score_never_gets_override_regardless_of_history(self):
        """The override must be bounded to a narrow borderline band -
        it must NEVER apply to a confidently-high fraud score, even
        with a clean signal and strong history. This is what keeps the
        override from becoming a general history-overrides-fraud
        escape hatch."""
        from pipeline import score_transaction
        txn = self._make_txn(agent_age_days=500, device_ip_consistency=1,
                              user_past_over_budget_kept_rate=0.9,
                              order_price=7000, payment_mode="COD",
                              user_account_age_days=400)
        result = score_transaction(txn)
        assert result["fraud_risk_score"] >= 0.35, (
            f"Test fixture assumption broken: expected a confidently-high "
            f"score >= 0.35, got {result['fraud_risk_score']} — this test "
            f"needs recalibrating if the model changed."
        )
        assert result["decision"] == "HOLD_FRAUD_REVIEW"'''

if old_class not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old_class, new_class)

with open(path, "w") as f:
    f.write(content)

print("patched successfully")
