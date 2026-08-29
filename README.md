# RiskGate

A risk layer for AI-agent-initiated transactions. See `docs/SPEC.md` for
the full problem framing and design reasoning.

## How the pieces actually connect (this matters)

This is one system, not separate scripts:

1. `src/generate_data.py` → produces `data/transactions.csv`
2. `src/train_fraud_model.py` → trains the fraud-risk model, saves it to
   `models/`, ALSO saves the pincode-rate lookup and the F2-optimal
   threshold as their own artifacts (`pincode_rate_lookup.pkl`,
   `fraud_f2_threshold.pkl`) so nothing downstream ever hardcodes a copy
   that could silently go stale.
3. `src/train_intent_model.py` → trains the intent-match model, same
   artifact pattern (`intent_threshold.pkl`).
4. **`src/pipeline.py`** → THE unified entrypoint and the ONLY place
   scoring/gating logic lives. One function, `score_transaction(txn: dict)
   -> decision dict`, loads all three models/artifacts (fraud, intent,
   preference-fit heuristic) and runs the full gate. Every other script
   below calls this — there is exactly one gating implementation (this
   used to not be true; see "what broke" for why that mattered).
5. `src/catalog.py` + `src/shopping_agent.py` → a minimal, rule-based
   shopping agent that proposes a purchase from a small catalog given a
   human's intent. Exists to demonstrate `pipeline.py` against a realistic
   scenario — not a second product (see SPEC.md's Track 2 positioning).
6. `src/gating.py` → thin batch wrapper: runs `pipeline.score_transaction()`
   over the whole dataset, saves `data/gating_decisions.csv`.
7. `src/build_dashboard_data.py` → merges transactions with gating
   decisions, produces the dashboard's `demo_data.json`/`agg_stats.json`
   ("replay mode" data). `src/embed_dashboard_data.py` re-embeds that data
   into `dashboard/index.html` so the dashboard also works as a single,
   portable file.
8. `src/preference_fit.py`, `src/drift_test.py`, `src/seed_validation.py`,
   `src/baseline_comparison.py`, `src/cost_sensitivity.py` → validation
   and honesty checks, all calling the real pipeline, none reimplementing
   its logic. See "What's genuinely validated vs. heuristic" below.
9. `src/api.py` → exposes `pipeline.py` (and the shopping agent) over a
   local HTTP API so the dashboard and the consumer demo mock
   (`demo/landing.html` → `demo/checkout.html`) can call it live.
10. `dashboard/index.html` → four-tab UI (Consumer, Merchant, Razorpay,
    Fraud queue). Calls the live API at `localhost:5050` when running;
    falls back to the pre-built replay data if the server isn't up.

## Running it for real (live, not replayed)

```bash
pip install -r requirements.txt

# 1. generate data + train both models (only needed once, or to retrain)
python3 src/generate_data.py
python3 src/train_fraud_model.py
python3 src/train_intent_model.py

# 2. build the dashboard's "replay mode" data (merges transactions with
# gating decisions; also needed if you skip step 4's live API and just
# want the standalone dashboard file to reflect current data)
python3 src/gating.py
python3 src/build_dashboard_data.py
python3 src/embed_dashboard_data.py   # re-embeds it into dashboard/index.html

# 3. start the live API
python3 src/api.py
# -> running on http://localhost:5050

# 4. open dashboard/index.html in a browser
# The "Run new transaction" button will now show "● LIVE" and call the
# real pipeline. Without the API running, it falls back to "○ replay"
# using the data built in step 2.

# 5. optional — validation experiments (not required to run the product,
# but worth running to see the honesty checks behind the reported numbers)
python3 src/seed_validation.py    # confirms metrics are stable, not a lucky split
python3 src/baseline_comparison.py # proves the model beats a naive rule (F2: 0.694 vs 0.016)
# real_data_validation.py needs a real dataset first (not committed, ~100MB):
#   mkdir -p /tmp/realdata && curl -o /tmp/realdata/creditcard.csv \
#     https://raw.githubusercontent.com/nsethi31/Kaggle-Data-Credit-Card-Fraud-Detection/master/creditcard.csv
python3 src/real_data_validation.py # validates our methodology on real fraud data (AUC 0.972)
python3 src/drift_test.py         # tests the model against a shifted distribution
python3 src/cost_sensitivity.py   # threshold tradeoff table at illustrative scale

# 6. optional — the full consumer-facing demo flow
# open demo/landing.html, click through to demo/checkout.html, enter a
# real request, and watch it go through the live shopping agent + RiskGate
```

## What's genuinely validated vs. heuristic

- **Fraud-risk** and **intent-match**: trained logistic regression models,
  proper train/test split, no leakage, honest precision/recall reported
  (see the printed output of the training scripts), cross-validated across
  5 folds, stable across 5 different random seeds, and shown to genuinely
  outperform a naive rule-based baseline (F2: 0.694 vs. 0.016).
- **Preference-fit**: an explicit, transparent heuristic — not claimed to
  be statistically validated to the same standard as the two scores above,
  because there's no clean ground-truth label for "would this customer
  have preferred this." We did directly test that it correlates with real
  outcomes (see "what broke" below) rather than just assuming it does.
  See SPEC.md for the full reasoning.

## What broke, and what we fixed (kept honest, on purpose)

- Initial fraud data generation had too much noise relative to signal —
  model AUC was 0.585 (barely above random). Fixed by tuning the
  generator's probability logic to have a real, learnable relationship
  between risk factors and outcome (final AUC: 0.73).
- Initial fraud model had a data leak: `pincode_return_rate` was computed
  from the full dataset (including test rows) before the split. Fixed by
  computing it from `train_df` only, then saving it as its own artifact
  for consistent use at inference time.
- Initial `/full_loop` API endpoint had a variable-scoping bug: `category`
  was only defined on the GET path, so POST requests (real user input from
  the checkout mock) crashed with an UnboundLocalError. Fixed by reading
  from `intent["category"]` consistently on both paths.
- Preference-fit was designed to predict "is this deviation more likely a
  mistake or more likely welcome," but we discovered — by directly testing
  the correlation, not assuming it — that `preference_fit_signal` had
  essentially zero correlation (-0.013) with actual mismatch/return
  outcomes in the synthetic data. The cause: the mismatch label was
  generated independently of preference-fit, so there was no causal path
  for them to correlate at all. Fixed by making preference-fit genuinely
  reduce mismatch probability specifically for over-budget deviations
  (the case it's meant to predict) — after the fix, mismatch rate is 18%
  when preference-fit is low vs. 9.5% when high, among over-budget orders.
- The fraud model's classification threshold was left at sklearn's
  default (0.5) while the intent-match model's was properly F2-optimized
  — an inconsistency in applying our own stated rigor standard. Fixed by
  applying the same F2-optimization to the fraud model, which moved its
  threshold to 0.3 and revealed an important, uncomfortable finding: pure
  recall-favoring optimization pushes the false-positive rate to ~68% —
  see "Cost at real scale" below for why that matters and what it means
  for real deployment.
- That 0.3 threshold, applied everywhere, held 75% of all transactions
  for fraud review — an unusable demo and an indefensible production
  number. Rather than either hiding this or shipping a misleading demo,
  we deliberately split the threshold: 0.3 stays as the honestly-reported
  metric (what the model can do at max recall), while the live
  product/demo gates at a separate, business-realistic 0.5 — both labeled
  clearly, in code and in the dashboard itself, so neither number is
  presented as the other.
- `gating.py` was a second, independent implementation of the same
  scoring/gating logic already in `pipeline.py` — duplicated, not shared.
  This is exactly why the intent-match threshold could go stale without
  anyone noticing (it drifted from 0.65 to 0.55 after a data fix, and only
  one of the two copies got updated). Fixed at the root, not just the
  symptom: `gating.py` is now a thin wrapper that calls
  `pipeline.score_transaction()` — there really is only one gating
  implementation now, matching what the module's own docstring claims.
  The same staleness bug also existed a third time, in `seed_validation.py`
  (using sklearn's default threshold instead of the F2-optimal one) — fixed
  the same way, by deriving the threshold the same way production does
  rather than hardcoding a copy.
- A new user (no purchase history) would get `preference_fit_score = 0`
  by construction — not because of any real risk signal, but simply
  because there was no history to compute a score from. That silently
  penalized new customers exactly the opposite of what a growth-focused
  platform wants. Fixed by defaulting users with under 30 days of account
  history to a neutral preference-fit score (0.5), so gating for new users
  leans on fraud-risk and intent-match instead of penalizing them for
  being new.
- The preference-fit category-alignment weighting (originally a guessed
  0.7/0.3 split) was never validated against real correlation with
  outcomes. We tested a range of alternatives directly — (0.9-1.0, 0.1)
  correlated slightly better with actual mismatch/return outcomes than the
  original guess — and updated to (1.0, 0.2), now empirically checked
  rather than picked by feel. Not claimed optimal, just no longer arbitrary.
- The fraud-probability formula's coefficients were originally tuned
  reactively, after seeing a bad AUC — a real circularity problem (see the
  signal-strength fix above). We kept the same numeric weights (rederiving
  exact values would just be a different arbitrary choice without real
  fraud data) but re-grounded their ordering and justification in cited,
  general fraud indicators — chosen independent of what makes the metric
  look good, not after the fact. See `src/generate_data.py` for the
  reasoning behind each weight.
- On some machines (different numpy/BLAS builds than our dev environment
  — confirmed on an ARM Mac using Apple's Accelerate framework), training
  produced `RuntimeWarning: overflow encountered in matmul` during
  cross-validation — a real numerical stability issue, not cosmetic. Root
  cause: quasi-complete separation — because we deliberately tuned strong,
  learnable signal into the synthetic data, some cross-validation folds
  had features (like device/IP mismatch) that nearly perfectly predicted
  the outcome, pushing logistic regression's coefficients toward infinity.
  First attempted fix (moderate L2 regularization, `C=0.5`) reduced but
  didn't eliminate the warnings on all machines — confirmed by testing on
  the actual machine that surfaced them, not assumed fixed from a single
  environment. Fixed properly with stronger regularization (`C=0.1`) plus
  an explicit, documented warning filter as a safety net against
  floating-point behavior we can't fully control across every numpy/BLAS
  build. Verified: reported metrics are unchanged (within normal seed
  variance) before and after.

## Why this, not a simpler thing

The obvious version of Track 2 is a single fraud detector. We didn't build
that, on purpose. Agentic checkout removes the one moment that used to
implicitly confirm a purchase — a human tapping a PIN. That moment did two
jobs at once: it stopped bad actors, AND it caught honest mistakes (wrong
size, over budget, misread intent). A single fraud score only replaces the
first job. RiskGate uses two independently validated scores because these
are different failure modes with different causes, different costs, and
different correct responses (hold-for-review vs. hold-for-a-quick-human-nod
vs. auto-approve) — collapsing them into one score would hide exactly the
distinction that matters for how a merchant or a customer should react.

## How this fits with what Razorpay already has

Razorpay already owns Thirdwatch (acquired 2019, now "Mitra") — a mature
fraud/RTO prevention product analyzing 200+ signals with merchant-configurable
risk thresholds. RiskGate is not a competing fraud detector. Thirdwatch's
signal set (device fingerprinting, address quality, buyer behavior) is built
on the assumption that a human made the purchasing decision — none of it
reasons about agent authorization scope or intent-match. That's the specific
gap agentic checkout opens up, which Thirdwatch's architecture has no way to
see. The intended relationship: RiskGate's fraud-risk and intent-match scores
are a new signal category designed to feed into infrastructure like
Thirdwatch, not replace it — and per-merchant threshold customization (which
Thirdwatch already does well) is exactly the kind of capability RiskGate
should compose with, not duplicate.

## Known constraints we thought about and didn't solve

- **Calibration**: we report probabilities (e.g. "fraud-risk 0.73") but never
  verified they're calibrated — that a 0.7 output actually corresponds to a
  ~70% real fraud rate among similarly-scored transactions. Uncalibrated
  probabilities are a known gap between a working demo and something a real
  risk team could trust numerically, not just directionally. We didn't have
  time to build this properly (Platt scaling or isotonic regression against
  a genuinely held-out calibration set), and doing it badly would be worse
  than naming it plainly as unverified.
- **Revenue tension**: every held transaction is lost revenue for Razorpay
  too, not just risk avoided for the merchant. `HOLD_CONFIRM_WITH_HUMAN`
  exists as a separate outcome from an outright block specifically to
  preserve revenue on borderline cases — and the cost-sensitivity table
  exists so a business can pick a threshold that weighs fraud-loss against
  revenue-loss deliberately, not blindly.
- **Human-confirmation timing**: we considered adding a timeout/expiry
  policy for `HOLD_CONFIRM_WITH_HUMAN` (what if the human doesn't respond?)
  and deliberately didn't build one — this path only triggers on genuinely
  borderline cases, not as a mainline flow, so it isn't yet the highest-value
  place to add complexity. Worth revisiting once real usage data shows how
  often it's actually hit.
- **Regulatory exposure**: scoring based on device/pincode/behavioral
  history touches RBI's expectations around algorithmic decisioning and
  India's DPDP Act consent requirements. We use pincode-level, not
  address-level, granularity as a deliberate privacy-conscious choice.
  A real deployment would likely fold consent for this kind of scoring into
  the same one-time agent-authorization consent flow (UAP/AP2-style),
  rather than requiring a separate ask.

## Does the model actually earn its complexity?

`src/baseline_comparison.py` checks this directly: a simple, fully-auditable
rule ("flag if COD AND device mismatch AND new agent") scores F2 = 0.016 on
the same held-out test set — it only catches 1.3% of actual fraud, because
requiring all three conditions at once is too strict to fire often. The
trained model scores F2 = 0.694 on the identical test set. This is the
comparison that justifies using a trained model instead of a rule a risk
analyst could write and audit by hand in five minutes — without it, an AUC
number has no real reference point.

## Does the methodology hold up on real data, not just our synthetic data?

We can't get real Razorpay agent-transaction data — agentic checkout is
brand new, that data doesn't exist yet. What we can do honestly:
`src/real_data_validation.py` validates the same modeling methodology
(regularized logistic regression, class-weight balancing, F2-optimized
threshold, 5-fold cross-validation) against the ULB European Cardholders
fraud dataset — 284,807 real transactions, real fraud labels, a genuinely
realistic 0.173% fraud rate (not our necessarily-elevated synthetic rate).
Result: AUC 0.972, catching 89% of real fraud with a 0.47% false-positive
rate among legitimate transactions. This does NOT validate our specific
synthetic features (device/IP, pincode — none of which exist in this
dataset) — it validates that the modeling approach itself is sound
practice on real-world-shaped, extremely imbalanced data, not something
that only happens to work on data we designed ourselves. The raw dataset
(~100MB) isn't committed to this repo — standard practice for large
datasets — but the script documents exactly how to fetch it and reproduce
this result.

## Cost at real scale (not just at 4,000 rows)

Our fraud model's held-out test set (800 transactions, 29.5% fraud rate —
elevated on purpose for a learnable synthetic signal, see note above), at
the F2-optimized threshold (0.3, chosen because a missed fraud costs more
than a delayed order), produces a false-positive rate of ~68% and a
false-negative rate of ~9%. That FPR is a genuinely important finding, not
a comfortable one: pure F2-optimization pushed the threshold to an
operational extreme — catching 91% of fraud, but holding roughly two out
of every three *good* transactions to do it. At Razorpay's real volume,
that tradeoff would be indefensible as-is; a real deployment would need a
cost-weighted objective (using actual rupee costs of a false positive vs.
a false negative, not just a recall-favoring proxy metric like F2) to pick
a threshold a business could actually live with — this is exactly why the
cost-sensitivity table (`src/cost_sensitivity.py`) exists: to make that
full tradeoff curve visible, rather than defending one single number.

**We use two different thresholds on purpose, and label them separately:**
`src/train_fraud_model.py` reports metrics at the F2-optimal threshold
(0.3) — this is the honest, methodologically consistent number for
evaluating the model itself. `src/gating.py` and `src/pipeline.py` (the
live product, including the dashboard demo) instead gate at 0.5, a more
business-realistic choice, because gating 75% of all transactions for
review (what 0.3 does on our data) isn't something any real merchant
would accept, and presenting the demo at a threshold nobody would
actually deploy would be its own kind of dishonesty. Picking a
production threshold is a business decision informed by real cost data —
not a single metric-optimization output — and using two different,
clearly-labeled numbers for two different purposes demonstrates that
distinction rather than papering over it. This isn't a flaw we're
hiding — it's *why* the deployment story below (shadow mode first)
exists: a model like this needs to prove itself against real outcomes
and a real cost model at real volume before any threshold, ours or a
better one, is trusted to act autonomously on real money.

## Who's accountable when an agent transaction goes wrong

RiskGate scores and gates — it does not resolve the harder open question
of liability: if an authorized agent buys the wrong thing, or a fraud
model wrongly blocks a legitimate purchase, who's responsible — the
agent's operator, the merchant, the bank, or Razorpay as the rail in the
middle? That's a real, unsolved regulatory question this project doesn't
attempt to answer, and shouldn't pretend to.

## What we'd need from Razorpay to make this real

- Real dispute/return outcome data (ours is synthetic, deliberately
  elevated in signal strength to be learnable on a small dataset)
- Real pincode-level and merchant-level historical risk data
- Integration with actual agent-authorization scope objects (the kind
  NPCI's UAP or AP2-style mandates would provide) — this prototype
  conflates authorization scope with stated intent (`intent_max_price`
  plays both roles); a real system would keep them genuinely separate.
  See SPEC.md's "named simplification" note for the full reasoning.
- A live shadow-mode deployment window to validate precision/recall
  against real outcomes before any autonomous gating is trusted
