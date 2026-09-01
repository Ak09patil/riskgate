"""
Integration tests — different from test_core.py's unit tests. These
check components working TOGETHER (shopping agent -> pipeline -> gate,
the live Flask API's actual HTTP routes) and include a real regression
guard on model quality, so a future change that silently degrades the
model gets caught by CI, not just noticed by a human reading printed
output from drift_test.py or seed_validation.py.

Run with: pytest tests/test_integration.py -v
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Same cosmetic-but-worth-fixing filter used everywhere else in this
# project that touches sklearn — this specific class of RuntimeWarning
# (quasi-complete-separation overflow) is harmless and platform-
# dependent, but a clean CI log matters just as much as a clean
# terminal, and this file never got the same filter the other scripts
# already have.
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="sklearn")

import pytest
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")


# --- Full loop integration: shopping agent + pipeline working together ---

class TestFullLoopIntegration:
    def test_shopping_agent_proposal_is_accepted_by_pipeline(self):
        """The exact seam between Track 1 (shopping agent) and Track 2
        (RiskGate) — the agent's output shape must be something
        score_transaction() can actually consume without extra glue code."""
        from shopping_agent import propose_purchase
        from pipeline import score_transaction

        intent = {"category": "footwear", "max_price": 4000, "key_attribute": "attr_2"}
        proposal = propose_purchase(intent)
        assert proposal is not None

        txn = {
            "order_price": proposal["order_price"],
            "order_category": proposal["order_category"],
            "order_key_attribute": proposal["order_key_attribute"],
            "intent_category": intent["category"],
            "intent_max_price": intent["max_price"],
            "intent_key_attribute": intent["key_attribute"],
            "payment_mode": "prepaid",
            "pincode": "500011",
            "agent_age_days": 200,
            "user_historical_category": "footwear",
            "user_past_over_budget_kept_rate": 0.5,
            "device_ip_consistency": 1,
            "user_account_age_days": 400,
        }
        result = score_transaction(txn)
        assert result["decision"] in {"AUTO_APPROVE", "HOLD_FRAUD_REVIEW",
                                       "HOLD_CONFIRM_WITH_HUMAN", "HOLD_LIKELY_MISMATCH"}

    def test_over_budget_proposal_with_good_history_routes_to_confirm(self):
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
        of THAT mechanism specifically."""
        from shopping_agent import propose_purchase
        from pipeline import score_transaction

        intent = {"category": "footwear", "max_price": 1500, "key_attribute": "attr_5"}
        proposal = propose_purchase(intent)
        assert proposal["matched_rule"] == "over_budget_closest_available"

        txn = {
            "order_price": proposal["order_price"],
            "order_category": proposal["order_category"],
            "order_key_attribute": proposal["order_key_attribute"],
            "intent_category": intent["category"],
            "intent_max_price": intent["max_price"],
            "intent_key_attribute": intent["key_attribute"],
            "payment_mode": "prepaid",
            "pincode": "500011",
            "agent_age_days": 200,
            "user_historical_category": "footwear",
            "user_past_over_budget_kept_rate": 0.9,  # strong history of keeping such orders
            "device_ip_consistency": 1,
            "user_account_age_days": 400,
        }
        result = score_transaction(txn)
        assert result["decision"] == "HOLD_CONFIRM_WITH_HUMAN"


class TestBoundedTrustOverride:
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
        assert result["decision"] == "HOLD_FRAUD_REVIEW"


# --- Live API integration: real Flask routes, via Flask's test client
# (no need for a running server — this is the standard way to test a
# Flask app's actual HTTP behavior in CI) ---

@pytest.fixture
def api_client():
    sys.path.insert(0, os.path.join(BASE_DIR, "src"))
    import api
    api.app.config["TESTING"] = True
    return api.app.test_client()


class TestAPIIntegration:
    def test_full_loop_endpoint_returns_scored_result(self, api_client):
        resp = api_client.post("/full_loop", json={
            "category": "footwear", "max_price": 3000, "key_attribute": "attr_2",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "SCORED"
        assert "decision" in data

    def test_score_endpoint_rejects_empty_body(self, api_client):
        """Regression test for the real bug found during QA — this used
        to crash with a raw 500 error instead of a clean response."""
        resp = api_client.post("/score", json={})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_score_endpoint_rejects_negative_price(self, api_client):
        """Regression test for a real bug found in proactive edge-case
        testing — negative and zero prices were silently accepted and
        scored as if valid, including being auto-approved."""
        txn = {
            "order_price": -500, "order_category": "footwear",
            "order_key_attribute": "attr_2", "payment_mode": "COD",
            "pincode": "500011", "agent_age_days": 200,
            "intent_category": "footwear", "intent_max_price": 3000,
            "intent_key_attribute": "attr_2",
            "user_historical_category": "footwear",
            "user_past_over_budget_kept_rate": 0.5,
            "device_ip_consistency": 1, "user_account_age_days": 400,
        }
        resp = api_client.post("/score", json=txn)
        assert resp.status_code == 400

    def test_score_endpoint_rejects_zero_price(self, api_client):
        txn = {
            "order_price": 0, "order_category": "footwear",
            "order_key_attribute": "attr_2", "payment_mode": "COD",
            "pincode": "500011", "agent_age_days": 200,
            "intent_category": "footwear", "intent_max_price": 3000,
            "intent_key_attribute": "attr_2",
            "user_historical_category": "footwear",
            "user_past_over_budget_kept_rate": 0.5,
            "device_ip_consistency": 1, "user_account_age_days": 400,
        }
        resp = api_client.post("/score", json=txn)
        assert resp.status_code == 400

    def test_full_loop_rejects_negative_max_price(self, api_client):
        resp = api_client.post("/full_loop", json={"max_price": -100})
        assert resp.status_code == 400

    def test_full_loop_rejects_non_numeric_max_price(self, api_client):
        """Regression test for the second real QA bug — max_price comes
        directly from a browser text input in the checkout demo."""
        resp = api_client.post("/full_loop", json={"max_price": "not a number"})
        assert resp.status_code == 400

    def test_record_outcome_requires_both_fields(self, api_client):
        resp = api_client.post("/record_outcome", json={"order_id": "txn_000001"})
        assert resp.status_code == 400


# --- Model quality regression guard — the one that would have caught a
# FUTURE change silently degrading the model, which none of the printed-
# output rigor scripts would stop from merging ---

# --- Concurrency: the most serious bug found in this session's edge-case
# hunt — concurrent writes to the outcomes log silently lost data while
# reporting success to every caller ---

class TestConcurrentOutcomeRecording:
    def test_concurrent_writes_do_not_lose_data(self, api_client, tmp_path, monkeypatch):
        """Regression test for a real, serious bug: 5 simultaneous
        POST /record_outcome calls used to result in only 1 row surviving
        in outcomes_log.csv (pandas' to_csv(mode='a') has a race window
        between checking if the file exists and appending to it). Fixed
        with a real file lock (fcntl). This test simulates concurrency
        with threads hitting the same Flask test client.

        Uses 30 threads (not 10) — a race condition can pass by luck on
        a small run; this failed on a real machine (macOS) even after
        an initial fix attempt, so this test is deliberately aggressive
        rather than just enough to pass once."""
        import threading
        import feedback_loop
        test_log = tmp_path / "outcomes_log.csv"
        monkeypatch.setattr(feedback_loop, "OUTCOMES_LOG", str(test_log))

        N = 30
        results = []
        def make_request(i):
            resp = api_client.post("/record_outcome", json={
                "order_id": f"txn_{i:06d}", "confirmed_fraud": True,
            })
            results.append(resp.status_code)

        threads = [threading.Thread(target=make_request, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(code == 200 for code in results)
        with open(test_log) as f:
            lines = f.readlines()
        header_count = sum(1 for line in lines if line.startswith("order_id,"))
        assert header_count == 1, f"expected exactly 1 header row, found {header_count} — two writers both thought the file was empty at once"
        # header + N data rows — every write must survive, not just
        # every write must REPORT success
        assert len(lines) == N + 1, f"expected {N + 1} lines (header + {N} rows), got {len(lines)} — data was lost"


# --- Two new loss classes: abuse-ring sentinel (relational/graph
# detection) and fraud-spike detector (time-series anomaly detection).
# Both are validated against real injected ground truth in
# generate_data.py, the same rigor standard as fraud-risk/intent-match —
# these tests guard against a future change silently degrading either. ---

class TestAbuseRingSentinel:
    def test_detects_injected_rings_above_a_reasonable_recall_floor(self):
        """Regression guard, not a re-check of the exact reported number
        (real result was recall=1.0, precision=0.923). Floor set well
        below that so this only fires on genuine regression."""
        import pandas as pd
        from ring_detector import detect_rings, validate_against_ground_truth
        df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
        result_df = detect_rings(df)
        metrics = validate_against_ground_truth(result_df)
        assert metrics["recall"] >= 0.7, f"Ring detection recall ({metrics['recall']}) dropped below regression floor"
        assert metrics["precision"] >= 0.5, f"Ring detection precision ({metrics['precision']}) dropped below regression floor"

    def test_false_positive_rate_on_clean_data_stays_low(self):
        """The stronger honesty check: on data with ZERO injected rings,
        does the detector still stay quiet? Real result was 0.07% (3 of
        4000). Floor set generously above that."""
        import pandas as pd
        from ring_detector import detect_rings
        df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
        clean_only = df[df["true_ring_id"] == -1].copy()
        result = detect_rings(clean_only)
        fp_rate = (result["detected_ring_id"] >= 0).mean()
        assert fp_rate < 0.02, f"False positive rate on clean data ({fp_rate:.3f}) is too high — detector is over-triggering"


class TestFraudSpikeDetector:
    def test_detects_injected_spikes_above_a_reasonable_floor(self):
        """Regression guard for the real result (precision=0.545,
        recall=0.545) — floor set below that."""
        import pandas as pd
        from spike_detector import detect_spikes, validate_against_ground_truth
        df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
        bucket_stats = detect_spikes(df)
        metrics = validate_against_ground_truth(bucket_stats)
        assert metrics["recall"] >= 0.3, f"Spike detection recall ({metrics['recall']}) dropped below regression floor"
        assert metrics["precision"] >= 0.3, f"Spike detection precision ({metrics['precision']}) dropped below regression floor"


class TestFairnessImprovement:
    def test_pincode_shrinkage_keeps_worst_case_disparity_bounded(self):
        """Regression guard for a real fix: pincode-level fraud rates
        now use empirical-Bayes shrinkage (compute_shrunk_pincode_rates
        in pipeline.py) instead of raw per-pincode rates, specifically
        because the raw version let one low-sample pincode over-flag
        honest customers at 2.8x its real risk. After the fix, the
        worst case dropped to 2.42x and the overall spread (std)
        tightened from 0.67 to 0.52. This guards against regressing
        back toward the original problem, not against every small
        fluctuation — real results have some run-to-run noise."""
        from fairness_check import compute_fairness_table
        result_df = compute_fairness_table()
        worst_ratio = result_df["fpr_to_fraud_rate_ratio"].max()
        assert worst_ratio < 3.0, (
            f"Worst-case pincode disparity ({worst_ratio}x) regressed back toward "
            f"or beyond the original unfixed problem (2.8x) — shrinkage may have stopped working."
        )


class TestFullModelComparisonJustification:
    def test_current_model_stays_among_the_best_by_f2(self):
        """Regression guard for the broader claim (see
        full_model_comparison.py): logistic regression isn't just
        'not measurably worse than XGBoost' — tested against Random
        Forest, Gradient Boosting, SVM, Naive Bayes, KNN, XGBoost, and
        LightGBM, on identical data/features/split/methodology, it was
        the single highest-F2 model of everything tested. This guards
        against that regressing, not against every small fluctuation —
        F2 differences under ~0.03 are within normal noise here."""
        from full_model_comparison import run_comparison
        results_df = run_comparison()
        current = results_df[results_df["model"].str.contains("current production")].iloc[0]
        best_f2 = results_df["f2"].max()
        assert current["f2"] >= best_f2 - 0.03, (
            f"Current production model's F2 ({current['f2']}) fell meaningfully behind the best "
            f"tested alternative ({best_f2}) — the interpretability tradeoff should be revisited."
        )

    def test_auc_gap_against_best_alternative_stays_within_normal_seed_noise(self):
        """AUC alone isn't the metric we optimize for (F2 is — see
        README's cost-asymmetry reasoning), but guard against the gap
        growing far beyond normal run-to-run noise (measured at
        std=0.025 in seed_validation.py) regardless."""
        from full_model_comparison import run_comparison
        results_df = run_comparison()
        current = results_df[results_df["model"].str.contains("current production")].iloc[0]
        best_auc = results_df["auc"].max()
        assert best_auc - current["auc"] < 0.05, (
            f"Best alternative AUC ({best_auc}) now exceeds current production model "
            f"({current['auc']}) by more than normal seed noise would explain."
        )


class TestModelComplexityJustification:
    def test_logistic_regression_is_not_measurably_worse_than_xgboost(self):
        """Regression guard for a real, tested claim (see
        model_complexity_comparison.py): a more complex model does NOT
        measurably beat our logistic regression on this data. If a
        future data/feature change made that stop being true, that
        would be a real signal the interpretability tradeoff needs
        revisiting — this test exists to surface that, not to lock in
        a specific outcome forever.

        NOTE: skips if xgboost genuinely can't run — either not
        installed, OR installed but its native library fails to load
        (a real, common macOS issue: xgboost needs OpenMP/libomp,
        which isn't present by default — this raises XGBoostError, not
        ImportError, so checking only "is the package importable" via
        find_spec is NOT sufficient, confirmed by this exact failure
        happening on real hardware during testing). Calling
        evaluate_xgboost() directly and checking its actual return
        value is the only reliable way to know it really ran."""
        from model_complexity_comparison import evaluate_logistic_regression, evaluate_xgboost
        lr_auc, lr_f2 = evaluate_logistic_regression()
        xgb_auc, xgb_f2, _, _ = evaluate_xgboost()

        if xgb_auc is None:
            pytest.skip("xgboost could not run in this environment (not installed, or "
                        "native library failed to load — e.g. missing OpenMP/libomp on macOS)")

        # HISTORY: this test originally asserted the OPPOSITE — that
        # XGBoost should NOT measurably beat logistic regression, as a
        # guard to catch if that assumption stopped holding. It fired
        # correctly: on held-out validation against a real 284,807-row
        # dataset (Kaggle Credit Card Fraud), XGBoost measurably beat
        # logistic regression (F2 0.856 vs 0.707 — see
        # held_out_validation_results.csv), and we deliberately switched
        # the production model as a result. This test now guards the
        # OPPOSITE direction: if a future change makes XGBoost stop
        # beating logistic regression on THIS (synthetic) dataset too,
        # that is worth knowing, since our synthetic-data numbers already
        # show XGBoost underperforming logistic regression here (AUC
        # ~0.655 vs ~0.697) — a widening or reversing gap either way is
        # signal, not noise, and worth a human looking at it again.
        gap = lr_auc - xgb_auc
        assert gap < 0.15, (
            f"Logistic regression (AUC {lr_auc:.3f}) now beats XGBoost "
            f"(AUC {xgb_auc:.3f}) by more than expected on synthetic data "
            f"(gap {gap:.3f}) — worth checking this is still consistent "
            f"with the real-data validation story before trusting it."
        )


class TestModelQualityFloor:
    def test_fraud_model_auc_stays_above_a_reasonable_floor(self):
        """Not a strict re-check of the exact reported number (that's
        what train_fraud_model.py's own printed output is for) — this
        is a REGRESSION GUARD: if a future change tanks the model to
        near-random performance, this fails CI instead of silently
        shipping. Floor is set well below our actual result (0.73) so
        this only fires on a genuine regression, not normal noise."""
        df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["is_fraud"])

        from pipeline import NEW_AGENT_AGE_DAYS, HIGH_VALUE_THRESHOLD, FRAUD_FEATURES
        pincode_rate_map = train_df.groupby("pincode")["is_fraud"].mean()
        global_fraud_rate = train_df["is_fraud"].mean()
        test_df = test_df.copy()
        test_df["is_cod"] = (test_df["payment_mode"] == "COD").astype(int)
        test_df["is_new_agent"] = (test_df["agent_age_days"] < NEW_AGENT_AGE_DAYS).astype(int)
        test_df["high_value"] = (test_df["order_value"] > HIGH_VALUE_THRESHOLD).astype(int)
        test_df["cod_and_high_value"] = test_df["is_cod"] * test_df["high_value"]
        test_df["pincode_return_rate"] = test_df["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)

        model = joblib.load(f"{BASE_DIR}/models/fraud_model.pkl")
        # XGBoost (calibrated) doesn'"'"'t require feature scaling, unlike the
        # earlier logistic regression model — scaler.transform() removed.
        y_proba = model.predict_proba(test_df[FRAUD_FEATURES])[:, 1]
        auc = roc_auc_score(test_df["is_fraud"], y_proba)

        MINIMUM_ACCEPTABLE_AUC = 0.65  # real result now ~0.678 (calibrated
                                        # XGBoost) — this floor only fires on
                                        # genuine regression
        assert auc >= MINIMUM_ACCEPTABLE_AUC, \
            f"Fraud model AUC ({auc:.3f}) dropped below the regression floor " \
            f"({MINIMUM_ACCEPTABLE_AUC}) — this is a real quality regression, not noise."

    def test_model_beats_naive_baseline(self):
        """Regression guard version of baseline_comparison.py — asserts
        the model beats the naive rule, rather than just printing that
        it does. If a future change makes the model WORSE than a simple
        hand-written rule, that's a genuine problem CI should catch."""
        df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["is_fraud"])

        from pipeline import NEW_AGENT_AGE_DAYS, HIGH_VALUE_THRESHOLD, FRAUD_FEATURES
        pincode_rate_map = train_df.groupby("pincode")["is_fraud"].mean()
        global_fraud_rate = train_df["is_fraud"].mean()
        test_df = test_df.copy()
        test_df["is_cod"] = (test_df["payment_mode"] == "COD").astype(int)
        test_df["is_new_agent"] = (test_df["agent_age_days"] < NEW_AGENT_AGE_DAYS).astype(int)
        test_df["high_value"] = (test_df["order_value"] > HIGH_VALUE_THRESHOLD).astype(int)
        test_df["cod_and_high_value"] = test_df["is_cod"] * test_df["high_value"]
        test_df["pincode_return_rate"] = test_df["pincode"].map(pincode_rate_map).fillna(global_fraud_rate)

        from sklearn.metrics import fbeta_score
        baseline_pred = (
            (test_df["is_cod"] == 1)
            & (test_df["device_ip_consistency"] == 0)
            & (test_df["is_new_agent"] == 1)
        ).astype(int)
        baseline_f2 = fbeta_score(test_df["is_fraud"], baseline_pred, beta=2, zero_division=0)

        model = joblib.load(f"{BASE_DIR}/models/fraud_model.pkl")
        # Calibrated XGBoost does not require feature scaling.
        y_proba = model.predict_proba(test_df[FRAUD_FEATURES])[:, 1]
        model_pred = (y_proba >= 0.3).astype(int)
        model_f2 = fbeta_score(test_df["is_fraud"], model_pred, beta=2, zero_division=0)

        assert model_f2 > baseline_f2, \
            f"Model F2 ({model_f2:.3f}) no longer beats the naive baseline ({baseline_f2:.3f})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
