# RiskGate — Testing & Verification Log

This documents the actual testing history of this project — real
commands, real output, real bugs found. Not a curated highlight reel;
this is what testing genuinely looked like, including the failures.

## 1. Automated tests (CI)

Two tiers, both run automatically on every push via GitHub Actions
(`.github/workflows/tests.yml`) — see the badge at the top of the README
for live status.

**`tests/test_core.py`** — 13 unit tests on individual functions:
score_transaction() always returns a valid decision and in-range
probabilities, a clean transaction is never flagged, a high-risk
transaction is always flagged, the cold-start fix (new users get
neutral preference-fit, not penalized) as a regression test, intent-
match correctly detects category mismatches, the shopping agent returns
real catalog items and respects budget, and scoring is deterministic.

**`tests/test_integration.py`** — 8 tests on components working
together, not in isolation:
- The exact seam between the shopping agent and RiskGate (agent's
  output must be directly consumable by score_transaction())
- The scenario the whole three-score architecture was designed around:
  an over-budget proposal with a strong purchase history must route to
  HOLD_CONFIRM_WITH_HUMAN, not silently auto-approve or block
- The live Flask API's actual HTTP routes, via Flask's test client —
  including regression tests for the two real crash bugs found during
  the final QA pass (`/score` on empty input, `/full_loop` on
  non-numeric `max_price`)
- A model-quality regression floor: asserts the fraud model's AUC
  doesn't silently degrade below 0.65 (our real result is ~0.73) if a
  future change breaks something the printed-output rigor scripts alone
  wouldn't catch in CI
- A regression guard that the model must keep beating the naive
  baseline rule, not just print that it currently does

21 tests total, run with: `pytest tests/ -v`

## 2. Manual verification scripts (rigor checks, not pass/fail)

These print detailed output for a human to read and judge, rather than
a simple pass/fail — appropriate for things like "is this model
actually calibrated" where the answer is a nuanced number, not
true/false.

- `src/seed_validation.py` — 5 different random seeds, confirms stable results
- `src/drift_test.py` — tests the model against a shifted distribution
- `src/baseline_comparison.py` — proves the model beats a naive rule (F2: 0.699 vs 0.016)
- `src/real_data_validation.py` — validates methodology on a real public fraud dataset (AUC 0.972)
- `src/calibration_check.py` — checks and fixes probability calibration
- `src/fairness_check.py` — checks for geographic over-flagging bias
- `src/cost_sensitivity.py` — threshold tradeoff table at illustrative scale

## 3. Real device verification (cross-machine testing)

Every feature in this repo was verified on a second, independent
machine (a real Mac, different OS/numpy/BLAS build from the primary dev
environment) — not just assumed to work because it worked once. This
is what actually caught most of the bugs below; several never appeared
in the original dev environment at all.

## 4. Bugs actually found during testing, and how

This is the honest record — testing that never finds anything usually
means the testing wasn't looking hard enough.

| Bug | How it was found | Fix |
|---|---|---|
| Data leakage in fraud model (pincode rate computed on full dataset, including test rows) | Code review during initial build | Compute train-only, save as separate artifact |
| Weak synthetic signal (near-random AUC) | Model evaluation showed AUC ~0.58 | Retuned generator's signal strength |
| `gating.py` was a duplicate implementation of `pipeline.py`'s logic | A threshold changed in one copy, not the other — caught when numbers stopped matching | Made `gating.py` a thin wrapper, one implementation |
| Same staleness bug, a third time, in `seed_validation.py` | Found by systematically checking every file for the same pattern after finding it twice | Import shared threshold from `pipeline.py` |
| `preference_fit_signal` had ~zero correlation with real outcomes | Directly tested the correlation instead of assuming it worked | Fixed the causal link in the data generator |
| Preference-fit weighting (0.7/0.3) was an unvalidated guess | Tested 5 alternative weightings against real correlation | Updated to the empirically better-supported value |
| Cold-start bug: new users penalized for lacking history | Traced through the pipeline logic by hand | Default new users to neutral (0.5), not 0 |
| RuntimeWarning: overflow during training | **Only appeared on a second, real device** — never in the original dev environment | Stronger regularization (C=0.1) + documented warning filter |
| Same overflow warning, in 4 more files that also call the model | Systematically re-ran every script with warnings visible after the first fix | Added the same filter to all affected files |
| `order_id` used `uuid.uuid4()`, not seeded — different every run | A rebuilt dataset broke a real user-recorded outcome — order_id in the dashboard no longer matched | Made order_id deterministic (`txn_{i:06d}`) |
| The order_id fix itself had a second bug — pandas silently read the zero-padded numeric string as an integer, stripping the padding | Checked the dtype explicitly, not just "does it look right" | Made the ID non-numeric (`txn_` prefix) so pandas can't misread it |
| 6 files had their own hardcoded copy of the fraud feature list | Adding one new feature (`cod_and_high_value`) required updating `pipeline.py`, which revealed the other 5 never got the same list | Import `FRAUD_FEATURES` from `pipeline.py` everywhere |
| `/score` API endpoint crashed with a raw 500 error on empty input | Deliberately tested malformed input as part of a final QA pass | Added input validation with a clean error response |
| `/full_loop` crashed on non-numeric `max_price` | Same QA pass — this field comes directly from a live browser input | Added type validation with a clean error response |
| Fraud queue's Approve/Reject buttons had no double-click protection | Reviewed for race conditions during the same QA pass | Added the same disable-while-pending pattern used elsewhere |
| A broken JS comment (missing `//`) silently killed the entire dashboard's interactivity | A user reported clicking a button did nothing; found via the browser console, not by reading the code | Fixed the comment; added a real `node --check` syntax test to the verification process, replacing a weaker regex-based check |
| Restructuring the checkout confirmation flow left a mismatched function-closing bracket | Caught immediately by the same `node --check` syntax test, before it ever reached a user | Fixed the bracket mismatch |

## 5. Fresh-clone verification

Before considering this submission-ready, the actual public GitHub repo
(not local files) was cloned fresh into a clean directory, dependencies
installed from scratch, and the full pipeline + test suite run against
it — to catch anything that only reproduces from a genuinely clean
checkout, which is exactly what a judge running this repo will do.

```bash
git clone https://github.com/Ak09patil/riskgate.git
cd riskgate
pip install -r requirements.txt
python src/generate_data.py
python src/train_fraud_model.py
python src/train_intent_model.py
pytest tests/ -v
```
