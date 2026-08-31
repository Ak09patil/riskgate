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
        auto-approve or block. If this breaks, the core thesis breaks."""
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
        scaler = joblib.load(f"{BASE_DIR}/models/fraud_scaler.pkl")
        y_proba = model.predict_proba(scaler.transform(test_df[FRAUD_FEATURES]))[:, 1]
        auc = roc_auc_score(test_df["is_fraud"], y_proba)

        MINIMUM_ACCEPTABLE_AUC = 0.65  # our real result is ~0.73 — this floor
                                        # only fires on genuine regression
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
        scaler = joblib.load(f"{BASE_DIR}/models/fraud_scaler.pkl")
        y_proba = model.predict_proba(scaler.transform(test_df[FRAUD_FEATURES]))[:, 1]
        model_pred = (y_proba >= 0.3).astype(int)
        model_f2 = fbeta_score(test_df["is_fraud"], model_pred, beta=2, zero_division=0)

        assert model_f2 > baseline_f2, \
            f"Model F2 ({model_f2:.3f}) no longer beats the naive baseline ({baseline_f2:.3f})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
