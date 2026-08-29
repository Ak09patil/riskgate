# RiskGate — Spec v1

## One-line pitch
A risk layer for AI-agent-initiated transactions. Agentic checkout removes the
human PIN-entry moment that used to silently confirm "yes, I actually want this."
RiskGate replaces that lost confirmation step with three scores that decide,
per transaction, whether to auto-approve, hold for fraud review, hold for a
quick human nudge, or block.

## Full loop (as actually built)
This is not just a risk detector in isolation — it's demonstrated against a
real end-to-end scenario: a minimal, rule-based **shopping agent**
(`src/shopping_agent.py`, matching against `src/catalog.py`) proposes a
purchase from a small catalog given a human's stated intent, and RiskGate
(`src/pipeline.py`) scores and gates that proposal. A local API
(`src/api.py`) exposes this live; the dashboard (`dashboard/index.html`)
and a mock consumer checkout flow (`demo/landing.html`, `demo/checkout.html`
— takes real user input, not scripted) both call it. The shopping agent is
a deliberately simple test harness — NOT a Track 1 submission in its own
right. It exists to prove RiskGate works against a realistic proposal, not
a static CSV. **This is submitted under Track 2**; the shopping agent is
supporting evidence, not a second product.

## The three scores (in priority order — this order matters for the build)

### 1. Fraud-risk score  [LOAD-BEARING — full rigor, no compromise]
Classic bad-actor detection, adapted for agent transactions.
Features (as actually implemented, `src/train_fraud_model.py`):
device_ip_consistency, is_cod, pincode_return_rate, is_new_agent, high_value,
agent_age_days, order_value, user_account_age_days.
Label: `is_fraud` (0/1).
Validated with: train/test split, 5-fold cross-validation, precision, recall,
confusion matrix, F2-optimized threshold, false-positive cost framing,
5-seed stability check, and an adversarial drift test (`src/drift_test.py`).

### 2. Intent-match score  [LOAD-BEARING — full rigor, no compromise]
Did the agent stay within what it was actually told to do?
Features: category_match (bool), price_within_budget (bool + delta),
key_attribute_match (bool, e.g. size/variant).
Label: `is_return_or_mismatch` (0/1) — order got returned/disputed due to a
mismatch, NOT fraud.
Validated with: same rigor as #1, reported separately.

### 3. Preference-fit score  [LIGHTER, DIRECTIONAL — explicitly labeled as such]
Narrow job only: if an order deviates from stated intent (esp. over budget),
does this customer's history suggest the deviation is one they'd likely
welcome, rather than a probable return?
Actual formula (`pipeline.py`): `user_past_over_budget_kept_rate × category_alignment`
(1.0 if order category matches historical category, else 0.3) — capped at 1.0.
New users (under 30 days account history) get a neutral 0.5 instead, to avoid
penalizing them for having no history rather than any real risk signal.
NOT a recommendation signal. NOT used to suggest alternative products.
Explicitly scoped as heuristic, not statistically validated to the same
standard as #1 and #2 — this is stated openly in the README, not hidden.
We did directly test whether this heuristic actually correlates with real
outcomes (see README "what broke") — it initially didn't (a real bug in
how the synthetic labels were generated), and the fix is documented there.

## Why score #3 doesn't compete with Razorpay's neutrality
RiskGate never recommends a product or nudges toward higher spend. Score #3
only answers: "is this deviation more mistake-like or more welcome-like,
given history?" — feeding ONLY the gating decision (confirm-with-human vs.
auto-block), never a product suggestion. This keeps RiskGate strictly in the
risk/trust lane, not the merchandising lane.

## Gating logic (4 outcomes)
1. Low fraud-risk, high intent-match → AUTO-APPROVE
2. High fraud-risk (regardless of others) → HOLD, fraud review
3. Low fraud-risk, low intent-match, high preference-fit → HOLD, human
   confirm ("this deviates from budget, but matches your pattern — confirm?")
4. Low fraud-risk, low intent-match, low preference-fit → HOLD/BLOCK,
   likely mismatch — probable return

Every decision is logged with the scores and the specific signals that drove it.

**Two fraud thresholds, intentionally different, both labeled everywhere:**
`train_fraud_model.py` reports metrics at the F2-optimal threshold (0.3) —
the honest number for evaluating the model itself. The live product
(`pipeline.py`, `gating.py`, dashboard, API) gates at a separate,
business-realistic threshold (0.5), because gating 75% of transactions at
0.3 is operationally indefensible even though it's the "correct" answer to
pure recall-optimization. See README "Cost at real scale" for the reasoning.

**Cold-start handling:** a user with under 30 days of account history gets
a neutral preference-fit score (0.5) rather than a penalized low one, since
an empty history is "unknown," not "known to be a poor fit." Gating for new
users leans on fraud-risk and intent-match instead.

## Data schema (one transaction record, as actually generated)

**Order facts:** order_id, order_value, category, payment_mode, pincode, timestamp

**Agent facts:** agent_id, agent_age_days, intent_category, intent_max_price,
intent_key_attribute

**Actual order (what was bought):** order_category, order_price, order_key_attribute

**User history:** user_id, user_historical_avg_order_value, user_historical_category,
user_account_age_days, device_ip_consistency, user_past_over_budget_kept_rate

**Labels:** is_fraud (0/1), is_return_or_mismatch (0/1)

**A named simplification worth being explicit about:** our core framing is
"the agent is *authorized*, but still makes a wrong call" — but this
prototype doesn't model authorization scope as a separate, enforced field
from stated intent. `intent_max_price`/`intent_category` play double duty
as both "what the human asked for" and "what the agent is allowed to
spend." A real system (especially one integrating with UAP/AP2-style
authorization mandates) would keep these genuinely separate: a
cryptographically-enforced authorization scope the agent cannot exceed,
and a softer stated intent the agent is trying to satisfy within that
scope — RiskGate's intent-match score would then check adherence to
*intent*, while a different, upstream system enforces the hard
*authorization* boundary. We conflated them here to keep the prototype's
scope tractable in the time available.

## Explicit scope boundary (state this clearly in README)
RiskGate does NOT solve agent identity/authentication security (e.g. spoofed
or compromised agents) — that's a separate, adjacent problem. RiskGate assumes
the agent's authorization is valid and evaluates the transaction's risk
GIVEN that authorization.

## Deployment story
Shadow mode first (score + log, no blocking) → limited autonomy (auto-approve
only, no auto-block) → full gating, once validated against real outcomes.
(See README "Cost at real scale" for why this staged rollout matters —
our synthetic metrics should not be trusted at real volume without it.)

## Scope decisions made during the build
Multi-agent orchestration (real agent-to-agent negotiation) was considered
and deliberately cut — the shopping agent is intentionally simple and
rule-based, not LLM-driven, to keep it debuggable and to protect time spent
on the two load-bearing scores, which needed to be bulletproof. See README
"Why this, not a simpler thing" for the full reasoning.
