# RiskGate — System Specification

Document status: v2. Reasoning and narrative for the decisions referenced
here are recorded in `docs/ARCHITECTURE.md` (design rationale) and
`docs/DECISION_LOG.md` (chronological engineering history). This document
states the system's contract precisely; it does not argue for it.

---

## 1. Purpose

RiskGate is a risk-scoring and gating layer for AI-agent-initiated
transactions. Given a proposed purchase from an authorized agent, RiskGate
returns one of five gating decisions, derived from three independently
computed scores.

## 2. System boundary

| In scope | Out of scope |
|---|---|
| Risk assessment of an already-authorized agent transaction | Agent identity/authentication (spoofed or compromised credentials) |
| Fraud-risk, intent-match, and preference-fit scoring | Full authorization-scope enforcement (conflated with stated intent in this prototype - see Sec 9) |
| Batch and live (per-transaction) gating via one shared entrypoint | Continual/online model retraining (periodic retraining only - see Sec 9) |

Full detail on each out-of-scope item is in Section 9.

## 3. System overview

```
human intent -> shopping agent (src/shopping_agent.py) -> proposed purchase
                                                                |
                                                                v
                              score_transaction() (src/pipeline.py)
                                                                |
                                                                v
                                                        gating decision
```

`score_transaction(txn: dict) -> dict` in `src/pipeline.py` is the single
entrypoint. All callers - the live API (`src/api.py`), the dashboard, the
checkout demo, and batch scoring - call this one function. There is no
separate implementation for batch vs. live scoring.

The shopping agent (`src/shopping_agent.py`, matching against
`src/catalog.py`) is a supporting test harness, not part of the submission
itself: a rule-based matcher that proposes a purchase from a small catalog
given a stated intent, used to exercise RiskGate against realistic
proposals rather than a static CSV.

## 4. Score definitions

### 4.1 Fraud-risk score

| Property | Value |
|---|---|
| Model | Calibrated XGBoost (`CalibratedClassifierCV` wrapping `XGBClassifier`) |
| Output | `fraud_risk_score`, float in [0, 1] |
| Label | `is_fraud` (0/1) |
| Rigor tier | Load-bearing - full validation, no compromise |

**Input features:** `device_ip_consistency`, `is_cod`, `pincode_return_rate`,
`pincode_ring_rate`, `is_new_agent`, `high_value`, `cod_and_high_value`,
`agent_age_days`, `order_value`, `user_account_age_days`.

**Validation performed:** train/test split, 5-fold cross-validation,
precision, recall, confusion matrix, F2-scanned threshold, 5-seed
stability check, adversarial drift test (`src/drift_test.py`), Platt
calibration with a verified Brier-score improvement, empirical-Bayes
pincode fairness audit with bootstrap confidence intervals, baseline
comparison against a naive rule, and an 8-model architecture comparison
on both synthetic and real external data. Full methodology: Section 7.

### 4.2 Intent-match score

| Property | Value |
|---|---|
| Model | Logistic regression |
| Output | `intent_match_confidence`, float in [0, 1] |
| Label | `is_return_or_mismatch` (0/1) - a return/dispute caused by mismatch, not fraud |
| Rigor tier | Load-bearing - full validation, no compromise |

**Input features:** `category_match` (bool), `price_within_budget`
(bool + delta), `key_attribute_match` (bool - size/variant).

**Validation performed:** same standard as Section 4.1, reported separately.

### 4.3 Preference-fit score

| Property | Value |
|---|---|
| Model | None - explicit heuristic formula |
| Output | `preference_fit_score`, float in [0, 1] |
| Rigor tier | Lighter, directional - explicitly not held to Sections 4.1/4.2's statistical standard |

**Formula** (`pipeline.py`):
`user_past_over_budget_kept_rate x category_alignment`, where
`category_alignment = 1.0` if the order category matches the user's
historical category, else `0.3`; result capped at 1.0. Users with under
30 days of account history receive a neutral `0.5` instead (cold-start
handling - an empty history is unknown, not known to be a poor fit).

**Scope constraint:** feeds only the gating decision
(`HOLD_CONFIRM_WITH_HUMAN` vs. `HOLD_LIKELY_MISMATCH`) - never a product
recommendation or an alternative-product suggestion. This is a scope
boundary, not an implementation detail: RiskGate does not perform a
merchandising function.

## 5. Gating logic

Evaluated in order; each step short-circuits the next.

| Step | Condition | Outcome |
|---|---|---|
| 1 | `order_value > Rs 25,000` (circuit breaker) | `HOLD_FRAUD_REVIEW` |
| 2 | `fraud_risk_score >= 0.45` | `HOLD_FRAUD_REVIEW` |
| 3a | `0.25 <= fraud_risk_score`, AND borderline (`< 0.30`) AND `user_past_over_budget_kept_rate >= 0.8` AND `device_ip_consistency == 1` | `HOLD_CONFIRM_WITH_HUMAN` (bounded trust override) |
| 3b | `0.25 <= fraud_risk_score`, override conditions not met | `HOLD_QUICK_VERIFY` |
| 4 | `fraud_risk_score < 0.25` AND `intent_match_confidence >= 0.6` | `AUTO_APPROVE` |
| 5a | `fraud_risk_score < 0.25` AND `intent_match_confidence < 0.6` AND `preference_fit_score >= 0.5` | `HOLD_CONFIRM_WITH_HUMAN` |
| 5b | `fraud_risk_score < 0.25` AND `intent_match_confidence < 0.6` AND `preference_fit_score < 0.5` | `HOLD_LIKELY_MISMATCH` |

Every decision is logged with the three scores and the specific signals
that produced it. `FRAUD_THRESHOLD` (0.25) and `FRAUD_THRESHOLD_HIGH`
(0.45) are defined once in `pipeline.py` and imported everywhere they're
used - never duplicated as a hardcoded copy.

## 6. Data contract

One transaction record, as generated by `src/generate_data.py` / consumed
by `score_transaction()`:

| Group | Fields |
|---|---|
| Order facts | `order_id`, `order_value`, `category`, `payment_mode`, `pincode`, `timestamp` |
| Agent facts | `agent_id`, `agent_age_days`, `intent_category`, `intent_max_price`, `intent_key_attribute` |
| Actual order | `order_category`, `order_price`, `order_key_attribute` |
| User history | `user_id`, `user_historical_avg_order_value`, `user_historical_category`, `user_account_age_days`, `device_ip_consistency`, `user_past_over_budget_kept_rate` |
| Labels | `is_fraud` (0/1), `is_return_or_mismatch` (0/1) |

**Known simplification:** `intent_max_price`/`intent_category` serve as
both "what the human asked for" and "what the agent is authorized to
spend" - a real authorization boundary is not modeled as a separate,
enforced field. See Section 9.2.

## 7. Evaluation methodology

| Aspect | Method |
|---|---|
| Objective function | F2 (recall weighted 2x over precision) - a missed fraud costs the full order value; an unnecessary hold costs friction only |
| Threshold selection | Full precision/recall/F2 scan across candidate thresholds (0.20-0.55), not a single value chosen by inspection |
| Cross-validation | 5-fold, on the training split, checked before test-set evaluation |
| Stability check | 5 random seeds; reported std used to judge whether any comparison gap is meaningful |
| Held-out evaluation | Confusion matrix, precision, recall, F1, ROC-AUC on a test split the model never trains on |
| Real-data validation | Model architecture validated separately against Kaggle Credit Card Fraud (284,807 real rows), independent of the synthetic-data threshold/CV work above |
| Fairness | Empirical-Bayes shrinkage on pincode-level false-positive rates, plus a bootstrap 95% CI on every reported disparity - a raw ratio alone is not treated as sufficient evidence of bias |
| Calibration | Brier score, before and after Platt scaling |

**Confusion matrix** (fraud-risk model, held-out test set, 815 rows, 30.3% fraud rate):

| | Predicted: Not Fraud | Predicted: Fraud |
|---|---|---|
| **Actual: Not Fraud** | 64 | 504 |
| **Actual: Fraud** | 11 | 236 |

504 false positives, 11 false negatives, at the F2-optimal threshold used for this specific evaluation run (distinct from the two-tier production threshold - Section 5). Reproducible via python src/train_fraud_model.py.

## 8. Deployment phases (specified, not yet executed beyond phase 0)

| Phase | Behavior |
|---|---|
| 0 - current | Live scoring and gating, demo/dashboard only, no real transaction volume |
| 1 - shadow mode | Score and log every transaction; no blocking. `feedback_loop.py` implements the comparison-against-real-outcomes mechanism this phase needs |
| 2 - limited autonomy | Auto-approve only; no auto-block |
| 3 - full gating | All five outcomes active, only after phase 1/2 validate precision/recall against real outcomes |

## 9. Out-of-scope boundary

RiskGate scores risk given a valid authorization. The following are
explicitly not solved by this system:

**9.1 Agent identity/authentication security.** A spoofed or compromised
agent credential, or a prompt-injection attack via a malicious product
listing, is a security/identity problem, not a risk-scoring problem.
RiskGate assumes the agent's authorization is valid and has no mechanism
to detect that the authorization itself has been compromised.

**9.2 Full separation of authorization scope from stated intent.** This
prototype conflates "what the human asked for" with "what the agent is
allowed to spend" in a single field. A production system integrating
with UAP/AP2-style mandates would keep these separate: a
cryptographically-enforced authorization boundary the agent cannot
exceed, checked upstream of RiskGate, with RiskGate's intent-match score
checking adherence to intent within that already-verified boundary.

**9.3 True online/continual learning.** Updating the model as new
human-confirmed outcomes arrive, rather than periodic full retraining, is
not implemented - concept drift, catastrophic forgetting, and the lack of
a clean real-time held-out set make this a materially harder problem than
this project's current scope. `feedback_loop.py`'s shadow-mode comparison
is a prerequisite step toward this, not an implementation of it. Listed
here as future scope, not a silently-omitted gap.

## 10. API schema

All endpoints served by src/api.py, running on http://localhost:5050.

| Endpoint | Method | Request | Response |
|---|---|---|---|
| /score | POST | Full transaction object (13 required fields - see Section 6) | fraud_risk_score, intent_match_confidence, preference_fit_score, decision, reason, order_id, agent_id, order_category, order_price, intent_max_price |
| /full_loop | POST | {category, max_price, key_attribute, allow_over_budget?} - all optional, a random realistic intent is generated if omitted | intent, proposed_product, matched_rule, agent_id, order_id, timestamp, order_category, order_price, intent_max_price, pincode, payment_mode, agent_age_days, device_ip_consistency, user_past_over_budget_kept_rate, plus every /score field |
| /explain | POST | Same 13 required fields as /score | fraud_risk_score, decision, top_contributing_signals (list of {feature, contribution, value}, sorted by contribution magnitude - see Section 4.1) |
| /detect_rings | GET | none | rings_detected, rings (list of {ring_id, size, pincode, order_ids}), cache_last_refreshed, validation_against_injected_ground_truth (synthetic data only) |
| /detect_spikes | GET | none | buckets_flagged, flagged_windows (list of {bucket_start, transaction_count, fraud_rate, z_score}), cache_last_refreshed, validation_against_injected_ground_truth (synthetic data only) |
| /record_outcome | POST | {order_id, confirmed_fraud, analyst_note?} | {status, order_id} |
| /feedback_status | GET | none | count, confirmed_fraud_count, confirmed_not_fraud_count, hold_fraud_review_match_rate (or status: no_outcomes_recorded_yet) |
| /simulate | GET | none | A random real transaction from the dataset, scored - same shape as /score's response |
| /fraud_batch_narrative | GET | none | narrative (string), narrative_source ("llm" or "template") |

All POST endpoints requiring transaction fields return 400 with an
explicit {"error": "..."} body on missing/invalid fields, rather than
a generic 500 - see api.py's validation blocks for the exact checks
(non-empty body, required fields present, order_price and
intent_max_price numeric and positive).

## 11. Design decisions out of scope for this document

The following were deliberately excluded from the build; reasoning for
each is in `docs/ARCHITECTURE.md`:
- Multi-agent orchestration for the shopping agent (kept rule-based)
- LLM-driven purchase negotiation
- A chargeback-evidence responder (a fourth detection capability considered and cut)
