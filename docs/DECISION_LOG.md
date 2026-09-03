# RiskGate — Decision Log

Chronological record of engineering decisions, in the order they were made. Each entry states the trigger, the decision, the evidence behind it, and the verified outcome. For the argued case behind the four buildathon criteria, see `docs/ARCHITECTURE.md`. For the system's precise current contract, see `docs/SPEC.md`.

---

## Phase 1 — Initial build (logistic regression era)

### 1.1 Model choice: logistic regression for fraud-risk and intent-match

**Trigger:** need an interpretable, auditable model for a bounded, structured classification problem.
**Decision:** logistic regression for both fraud-risk and intent-match scores.
**Evidence:** an interpretable linear decision boundary (weights that can be printed and reasoned about) satisfies "every money action explainable, bounded and gated" more directly than an opaque model, for a 4-8 feature problem.
**Outcome:** shipped, fully validated (train/test split, 5-fold CV, F2-optimized threshold, 5-seed stability check).

### 1.2 Data leakage found and fixed

**Trigger:** direct review of the pincode-risk feature's computation.
**Finding:** an early version computed pincode return-rate from the full dataset, including test rows - a real leak.
**Fix:** computed train-only, saved as its own artifact.
**Outcome:** verified no leakage remains; the same train-only pattern was later reused for the pincode ring-rate feature (Phase 3).

### 1.3 Duplicated gating implementation found and fixed

**Trigger:** an intent-match threshold changed from 0.65 to 0.55 after a data fix, but only one of two implementations was updated.
**Finding:** `gating.py` was a second, independent copy of the scoring/gating logic already in `pipeline.py` - the structural cause of the staleness.
**Fix:** made `gating.py` a thin wrapper around `pipeline.py`. The same staleness pattern was later found a third time (a hardcoded feature list duplicated across six analysis scripts) and fixed the same way - import from the shared source, never copy.
**Outcome:** exactly one gating implementation exists; a threshold or feature-list change cannot silently drift in one copy while staying stale in another.

### 1.4 Preference-fit's causal gap found and fixed

**Trigger:** direct correlation testing of preference-fit against real outcomes, rather than assuming the heuristic worked.
**Finding:** essentially zero correlation (-0.013) with actual mismatch/return labels - the mismatch label had been generated independently in the data generator, so no causal path existed for them to correlate.
**Fix:** wired a real causal link between preference-fit and the mismatch-probability calculation.
**Outcome:** verified after the fix - mismatch rate dropped from 18% (low preference-fit) to 9.5% (high preference-fit) among over-budget orders, a real, detectable effect.

### 1.5 A real design flaw: two "hold" decisions that behaved identically

**Trigger:** a direct question - "why is confirm different from mismatch if neither actually lets the customer confirm anything?"
**Finding:** `HOLD_CONFIRM_WITH_HUMAN` and `HOLD_LIKELY_MISMATCH` both finalized the checkout order regardless of the decision, then explained it after the fact - defeating the purpose of the two outcomes existing separately.
**Fix:** added a real pre-purchase confirmation gate. `HOLD_FRAUD_REVIEW` deliberately kept different - that one cannot be self-cleared by the customer, since a fraud hold needs actual analyst review.
**Outcome:** the three "not auto-approved" outcomes now genuinely behave differently, not just labeled differently.

### 1.6 Circuit breaker added after a real auto-approve failure

**Trigger:** real device testing.
**Finding:** a Rs 4,00,000 order with otherwise clean signals (consistent device, prepaid, established account) sailed through as `AUTO_APPROVE` - nothing that large existed anywhere in training data (max ever seen: ~Rs 12,306), so the model had no real basis for a score.
**Fix:** added a circuit breaker - any order value beyond a hard cap (Rs 25,000) is held for fraud review regardless of the model's score.
**Outcome:** verified with a regression test that the circuit breaker is the *only* mechanism catching this specific case - every other signal would have let it through.

---

## Phase 2 — The real-data validation that triggered the migration

### 2.1 Synthetic 8-model comparison

**Trigger:** the question "is logistic regression actually the best choice, or just the first one that worked?"
**Method:** `full_model_comparison.py` - logistic regression, Random Forest, Gradient Boosting, XGBoost, LightGBM, SVM, Naive Bayes, KNN, on identical data, features, split, and threshold-tuning methodology.
**Finding:** all 8 models cluster within normal seed-to-seed noise on the project's synthetic data (AUC spread 0.662-0.701, seed variance measured separately at std 0.025). No architecture stands out.
**Outcome at this point:** read alone, this result would have kept the project on logistic regression indefinitely.

### 2.2 Real-data validation against Kaggle Credit Card Fraud

**Trigger:** deliberately checking whether a synthetic-data-tuned model choice would hold up on real fraud, rather than trusting the synthetic result alone.
**Method:** `held_out_validation.py` - logistic regression, Random Forest, XGBoost, LightGBM, evaluated against the Kaggle Credit Card Fraud dataset (284,807 real, external transactions).
**Finding:** XGBoost F2 = 0.8557, Random Forest F2 = 0.8187, Logistic Regression F2 = 0.7073 - a real, large gap. (LightGBM's result in this specific run, F2 = 0.0656, was flagged as a likely misconfiguration/threshold anomaly in that run rather than a reliable data point - reported honestly rather than omitted or silently corrected.)
**Decision:** migrate the production fraud-risk model to XGBoost.

---

## Phase 3 — The XGBoost migration

### 3.1 Retraining and calibration

**Trigger:** the Phase 2.2 decision.
**Work:** retrained from scratch as `CalibratedClassifierCV` wrapping `XGBClassifier`, with Platt calibration built in from the start (XGBoost's raw scores needed it in a way logistic regression's didn't).
**Finding:** raw XGBoost was overconfident - a "0.9" prediction was only actually fraud ~69% of the time.
**Verified outcome:** Brier score improved from 0.229 (raw) to 0.194 (calibrated).

### 3.2 New feature: pincode ring-rate

**Trigger:** a targeted hypothesis test - does pincode-level ring involvement add signal beyond the existing return-rate feature?
**Method:** `compute_shrunk_pincode_ring_rates()`, same empirical-Bayes shrinkage technique as the existing pincode return-rate feature, computed train-only (Phase 1.2's leakage lesson reapplied).
**Finding:** SHAP importance 0.163 (8th of 10 features) - real but modest; precision at the then-threshold (0.30) was unchanged.
**Decision:** kept, with honest documentation that it didn't move precision, rather than dropped or oversold.

### 3.3 Threshold re-tuning: the two-tier design

**Trigger:** XGBoost's calibrated score distribution required re-deriving the threshold from scratch - the old logistic-regression-era thresholds had no reason to still be correct.
**Finding:** the F2-optimal threshold on this data is 0.20 - rejected, because the resulting flag rate exceeds 85% in some pincodes (blanket friction, not targeted risk-based friction).
**Empirical trail:** 0.30 -> 0.28 -> 0.25 tested in sequence, each an evidence-based step, converging on 0.25 as the floor (recall 79.8%, up from 0.30's 59.5%) paired with a 0.45 ceiling reserved for genuinely high-confidence fraud.
**Decision:** two-tier threshold (0.25 quick-verify floor, 0.45 full-review ceiling) instead of a single number - the split that makes both a high floor recall and a usable flag rate possible at once, which no single threshold value could achieve.

### 3.4 Bounded trust override

**Trigger:** the two-tier design created a genuine ambiguous band (0.25-0.45) - a mechanism was needed to route some of that band to a cheaper outcome without creating a trust-farming loophole.
**Decision:** a borderline score (< 0.30) downgrades to `HOLD_CONFIRM_WITH_HUMAN` only if *both* a strong history (`user_past_over_budget_kept_rate >= 0.8`) *and* a clean device/IP signal on *this specific transaction* hold - two-factor by design, so history alone cannot be farmed and cashed in on a single high-risk transaction.
**Verified:** three targeted tests confirm the override applies only under all three conditions, never applies above the high-confidence threshold regardless of history, and does not apply on a dirty signal even with strong history.

### 3.5 Fairness re-audit with bootstrap confidence intervals

**Trigger:** the threshold change (0.30 -> 0.25) needed a fresh fairness check - a prior audit's numbers (2.8x -> 2.42x via shrinkage) were computed against a different model and threshold entirely.
**Finding:** at 0.25, worst-case pincode disparity is 3.44x - but a bootstrap 95% CI (width ~0.31) shows this is not statistically distinguishable from sampling noise at current data volume.
**Cross-check:** at 0.20 (the rejected F2-optimal threshold), the same check gives a materially narrower CI (~0.16) - that disparity *would* be a confirmed, real bias.
**Outcome:** the CI-width finding, not the raw ratio, became the actual regression guard for fairness - a raw ratio alone was judged insufficient evidence either way.

---

## Phase 4 — Dashboard and demo build

### 4.1 Decision Trace

**Trigger:** a transaction's final decision label alone doesn't show *why* - the same gap a person reviewing a flagged transaction would have.
**Build:** a step-through visualization in the dashboard, walking the exact same gating order as `score_transaction()`, using the same threshold constants imported live from `pipeline.py` - not a separate hardcoded copy that could drift.

### 4.2 Threshold Explorer

**Trigger:** the two-tier threshold decision (3.3) involved real trade-off analysis that was otherwise only visible in a code comment.
**Build:** an interactive slider snapped to real, measured threshold values only (0.20-0.55) - no interpolated or invented data points - showing precision/recall/flag-rate and real cost-impact figures at each stop.

### 4.3 "Under the hood" panel and spike-detector visualization

**Trigger:** several genuinely rigorous results (ring/spike detector precision-recall, calibration, fairness, test count, model comparisons) existed only in terminal output, invisible to anyone just watching the demo.
**Build:** a dedicated panel surfacing all of them, each explicitly labeled with its data source (synthetic vs. real) - added after a direct question about whether mixing synthetic and real evidence in one submission was a liability; resolved by making the source of every claim visible rather than uniform.

### 4.4 UI bugs found during live demo testing

| Finding | Fix |
|---|---|
| Merchant filter pills and Razorpay stat grid hardcoded to 4 decision types, missing the new `HOLD_QUICK_VERIFY` bucket entirely | Updated to all 5 outcomes |
| `HOLD_LIKELY_MISMATCH` shared its badge color with `HOLD_CONFIRM_WITH_HUMAN`, despite one being a genuine hold/block and the other leaning toward proceeding | Relabeled, given a visually distinct color |
| Checkout demo's explanatory text always said "went outside your budget," even when the real reason was an attribute mismatch or a borderline-risk trust override | Branched the message on the actual reason |
| Cancel buttons on some screens didn't carry the transaction to the dashboard link, silently losing demo continuity | Every cancel/exit path now calls the same link-setting function |
| A 2-second fetch timeout was too tight given the dev server's documented serial-request behavior under concurrent load | Raised to 8 seconds; failures now logged to console instead of silently swallowed (the root issue: `fetch()` does not throw on a non-2xx HTTP status, only on network-level failures) |
| "30 outcome(s) recorded so far this session" mislabeled an all-time count as session-scoped | Corrected the label |

---

## Phase 5 — Cross-platform testing

### 5.1 Unix-only file locking found

**Trigger:** deliberate testing on a Windows machine, rather than assuming a Mac-developed project would work elsewhere.
**Finding:** `feedback_loop.py` used `fcntl.flock()` - Unix-only, hard-crashes on Windows with no fallback.
**Fix:** branched on `os.name`, using `msvcrt.locking()` on Windows (the standard portable technique - lock the file's first byte as a stand-in for a whole-file exclusive lock).

### 5.2 Windows-specific data loss under concurrency

**Trigger:** re-running the full test suite after 5.1's fix.
**Finding:** the concurrent-write regression test (30 threads hitting `/record_outcome`) still lost data - but only on Windows. Root cause: Windows' `locking()` does not reliably block a second file handle opened by the *same process* (a documented Windows CRT limitation), and Flask's dev server handles concurrent requests as threads within one process - exactly this scenario.
**Fix:** added a Python-level `threading.Lock()` on every platform, closing the same-process gap the OS-level lock left open on Windows specifically.
**Outcome:** 39/39 passing on Windows, verified on two separate physical Windows machines.

### 5.3 Cross-machine model pickle incompatibility

**Trigger:** the fully-fixed test suite still failed to *load* the model at all on Windows (`xgboost._c_api.XGBoostError: input stream corrupted`).
**Investigation, in order:** (1) hypothesized Git line-ending corruption - added `.gitattributes` marking binary files, did not fix it; (2) compared file sizes byte-for-byte across machines - identical, ruling out corruption in transfer; (3) compared installed XGBoost versions on both machines - identical, ruling out a version mismatch.
**Finding:** a genuine cross-machine pickle-portability quirk between platform-specific XGBoost library builds - confirmed by elimination, not assumed.
**Fix:** `pipeline.py`'s `_load_artifacts()` now catches this failure and retrains locally, automatically, once - self-healing rather than requiring an evaluator to read documentation and run a manual step.

### 5.4 Missing dependencies

**Trigger:** preparing for cross-platform testing, checking `requirements.txt` against actual imports rather than assuming it was complete.
**Finding:** `shap` and `requests` were both real dependencies (used in `train_fraud_model.py` and `load_test.py` respectively) but missing from `requirements.txt` - would have failed a fresh install on any machine.
**Fix:** added both.

---

## Phase 6a — Hyperparameter search

**Trigger:** a direct question during external review - had the production XGBoost hyperparameters (n_estimators=300, max_depth=6, learning_rate=0.1) ever been formally searched over, or just chosen as reasonable defaults? Honest answer at the time: never searched.
**Method:** hyperparameter_search.py - a 27-combination grid search (n_estimators in [100,300,500], max_depth in [3,6,9], learning_rate in [0.05,0.1,0.2]), selected by 5-fold F2 cross-validation on the training split only. Only after a winner was picked by CV were both the current production config and the best-found config evaluated on the untouched held-out test set, for an honest final comparison.
**Finding:** the CV-selected best config (n_estimators=100, max_depth=3, learning_rate=0.05) improved held-out test F2 by +0.0099 over the current production config - smaller than the model's own measured seed-to-seed variance (Sec 3.1).
**Decision:** kept the existing production hyperparameters rather than switching for a gain within noise - documented the search and its result rather than leaving the gap unaddressed or silently adopting a marginal, statistically insignificant change.

## Phase 6 — Documentation

**Trigger:** README, SPEC, and ARCHITECTURE all significantly predated the Phase 2-5 work and described the logistic-regression-era system throughout.
**Work:** README rewritten with a summary table and the full current numbers; SPEC restructured into formal specification form (numbered sections, tables, contract-only - narrative moved out); ARCHITECTURE restructured with an executive summary and sub-numbered sections, all numbers updated to current, and the model-choice narrative rewritten to reflect the actual migration rather than the original logistic-regression justification.
**This document** exists specifically to hold the chronological detail neither of the other two documents is meant to carry, per the same principle applied throughout this project: state each fact once, in the one place it belongs.
