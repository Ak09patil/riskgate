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
| **Concurrent writes to the outcomes log silently lost data** — 5 simultaneous requests all reported success, but only 1 row survived | A deliberate proactive concurrency test (not triggered by any user report) — sent 5 real simultaneous requests and checked the actual file contents, not just the API's response codes | Rewrote the write path with a real file lock (`fcntl`) — but the FIRST fix attempt was incomplete: checking emptiness with `f.tell()` passed 20/20 times in the sandbox but failed on a real Mac with a duplicate header row, because `f.tell()` right after opening in append mode isn't reliably 0-vs-nonzero across platforms. Found only because the automated test was actually run on a second, different machine, not trusted from a clean sandbox run. Fixed properly with `os.fstat().st_size`, a kernel-level check, not a buffered-stream one — verified 15/15 at a more aggressive 30 concurrent threads. |
| `/score` and `/full_loop` silently accepted negative or zero prices, scoring and even auto-approving them | A deliberate proactive adversarial input test, not a user report | Added explicit positive-value validation with clear error responses on both endpoints |

## 6. Proactive edge-case audit (not triggered by a bug report)

Before this pass, every bug above was found reactively — a user hit
something, or a specific hypothesis was tested. This pass was
different: deliberately trying to break the live, running system with
adversarial input, without a specific report to chase.

**Tested and found genuinely safe (not just assumed):**
- XSS-style injection (`<script>` tags) in the category field — safely
  rejected as "no catalog match," never reflected into any page
- Astronomically large price (₹999 billion) — correctly caught by the
  fraud model, held for review, not naively accepted
- An unseen pincode (never in the training data) — falls back to the
  global fraud rate cleanly, no crash
- `pattern_narrative.py` called with zero flagged transactions — returns
  a clean "no clusters detected" result, no crash on empty data
- Every place a live-typed user input reaches the DOM uses
  `.textContent` (auto-escaping), never `.innerHTML` with untrusted
  data — checked directly across both `dashboard/index.html` and
  `demo/checkout.html`, not assumed

**Tested and found genuinely broken (see table above for both):**
- Concurrent writes to the outcomes log
- Negative/zero price validation

This is deliberately a different kind of testing than everything
above it — proactive rather than reactive, adversarial rather than
representative. Both real findings from this pass now have their own
automated regression tests (`tests/test_integration.py`), so neither
can silently reappear.

## 7. Second proactive pass — deeper concurrency, defense-in-depth, and an honest limit

**Higher-concurrency stress test.** The original concurrency fix was
verified at 30 threads via Flask's in-process test client. Pushed
further: 100 real concurrent HTTP requests (via Python's `requests`
library and a thread pool, hitting the actual running server, not the
test client) — 100/100 succeeded, 100/100 rows survived, exactly one
header row. No sign of the race reappearing at higher load.

**Defense-in-depth gap, found and fixed.** `/full_loop`'s API-level
validation already rejected a non-positive `max_price` — but calling
`shopping_agent.propose_purchase()` **directly**, bypassing the API
entirely, had zero protection: a `-500` budget was silently treated as
"everything is over this budget" and matched to a real, positive-priced
product. Not a crash — worse, a plausible-looking wrong answer. Fixed
by validating at the function itself, not only at the one entry point
that happened to call it first. Two new automated tests cover this.

**An honest limit we're naming, not hiding: true cross-browser testing
was not performed.** Every screenshot and manual verification in this
project was done in Safari. The dashboard and checkout demo use
`AbortSignal.timeout()` (supported in Chrome 103+, Firefox 100+, Safari
16+, all mid-2022 or later) — safe for any reasonably current browser by
2026, and no other modern-only JS features (optional chaining, nullish
coalescing) are used, which reduces the risk further. But this is
reasoned confidence, not verified confidence — nobody has actually
clicked through this in Firefox or Edge. Worth doing before a live demo
if time allows.

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

**A real finding from this exact check, done again after the ring/spike
detector additions:** the committed `models/fraud_model.pkl` was trained
with scikit-learn 1.9.0, but a fresh install in a different environment
pulled 1.8.0 by default (`scikit-learn` was unpinned in
`requirements.txt`), producing an `InconsistentVersionWarning` when
loading the committed model directly. Confirmed harmless in this case
(predictions matched exactly), but the warning's own text says results
*could* be affected — a real risk for anyone who skips straight to
using the committed models instead of retraining locally (which the
README's primary documented flow already does, sidestepping this
naturally). Fixed by pinning `scikit-learn>=1.9.0` in
`requirements.txt`, so any fresh install matches or exceeds the version
the committed artifacts were trained with.
