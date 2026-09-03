# RiskGate

**An agent-transaction risk layer — fraud, intent-match, and preference-fit, gated.**

Built for the Razorpay AI Buildathon 2026, Track 2: AI Risk Manager.

When an AI shopping agent buys something on a customer's behalf, it can be fully authorized and still get it wrong — wrong size, over budget, misread intent. That's not fraud, and nobody was scoring for it. RiskGate scores three things on every agent-initiated transaction — **fraud risk**, **intent-match confidence**, and **preference-fit** — then gates it into one of five outcomes based on all three together.

---

## At a glance

| Claim | Number | Source |
|---|---|---|
| Model beats real-data baseline | **F2 0.856** vs. logistic regression's 0.707 | Real (Kaggle, 284,807 rows) |
| Model beats a hand-written rule | **F2 0.653** vs. 0.045 (14.5x) | Synthetic |
| Recall at production threshold | **79.8%** at 0.25 (vs. 59.5% at the original 0.30) | Synthetic |
| Ring detection | **92.3% precision, 100% recall** — 15/15 injected rings recovered | Synthetic, injected ground truth |
| Spike detection | **54.5% precision/recall**, 167 buckets scanned, 11 flagged | Synthetic, injected ground truth |
| Calibration | Brier **0.229 -> 0.194** (raw -> Platt-scaled) | Synthetic |
| Fairness | Worst-case disparity **3.44x**, bootstrap CI shows this is **not** statistically distinguishable from noise | Synthetic |
| Test suite | **39/39 passing**, macOS and Windows | Real (CI) |
| Throughput | **~168 req/s**, p50 57ms at concurrency 10 | Real (measured) |

Every number is labeled by source (real external data / measured system property, or synthetic self-generated data with injected ground truth where relevant) — neither is presented as the other.

---

## Documentation map

This README is the front door — comprehensive enough to read alone, but depth lives in three companion documents, each with one job:

| Document | Purpose |
|---|---|
| `docs/SPEC.md` | The system's precise technical contract — score definitions, gating logic as a formal table, data schema, evaluation methodology, explicit out-of-scope boundary |
| `docs/ARCHITECTURE.md` | The argued case for the four buildathon judging criteria (Problem Taste, Build Quality, AI Judgment, Failure Recovery) |
| `docs/DECISION_LOG.md` | The full chronological engineering history — every decision, in the order it was made, with trigger/evidence/outcome |

---

## Quick start

```
git clone https://github.com/Ak09patil/riskgate.git
cd riskgate
pip install -r requirements.txt
python src/api.py
```

Then, in a browser:
- `demo/landing.html` — the full guided demo
- `dashboard/index.html` — standalone dashboard, requires no live API and no real transaction data: it runs entirely against bundled mock/synthetic transaction data (`dashboard/demo_data.json`), so it can be reviewed and tested locally out of the box

If the model fails to load on first run, it retrains itself automatically, once — a known cross-machine pickle quirk, see `docs/ARCHITECTURE.md` Section 4 (Failure Recovery, item 7).

```
python -m pytest tests -v
```
43 tests, all passing, on both macOS and Windows — all run against mock transaction fixtures (`tests/test_core.py`, `tests/test_integration.py`), no real data or credentials required.

---
## Our principles

Not a formal document — the standard every claim in this project, and this README, is actually held to:

1. **Label the source of every number.** Real data and synthetic data answer different questions. Neither is dismissed, but neither is presented as the other.
2. **Report the honest result, not the flattering one.** Logistic regression beats XGBoost on our *own* synthetic data — that's documented, not hidden, because it's true and it's the reason we validated against real data before trusting the architecture.
3. **A gap in evidence is reported as a gap, not filled with a guess.** The fairness bootstrap CI shows genuine statistical noise, not "proven fair" — we say exactly that.
4. **Constants live in one place.** Thresholds are imported, not copy-pasted between the model, the dashboard, and the docs — a change in one place can't silently drift out of sync with a hardcoded copy elsewhere.
5. **Bugs get documented, not buried.** Every failure listed in `docs/ARCHITECTURE.md` and `docs/DECISION_LOG.md` is real, found through actual testing, not curated for the sake of looking thorough.

---

## Architecture, briefly

One entrypoint, `score_transaction(txn)` in `src/pipeline.py`, computes three scores and gates the result into one of five outcomes (auto-approve, quick-verify, confirm-with-human, fraud review, likely-mismatch). Full gating logic, thresholds, and the bounded trust override mechanism are specified precisely in `docs/SPEC.md` Section 5; the reasoning behind each threshold and the two-tier design is in `docs/ARCHITECTURE.md` Sections 2 and 3.1.

The model itself started as logistic regression and was migrated to calibrated XGBoost after real-data validation showed a large, real gap (F2 0.856 vs. 0.707) that the project's own synthetic benchmark did not show — full story in `docs/ARCHITECTURE.md` Section 3.1, full chronology in `docs/DECISION_LOG.md` Phases 2-3.

Two further detection layers — an abuse-ring sentinel and a fraud-spike detector — catch coordinated abuse and aggregate-rate anomalies that a single transaction's score can't see alone. Both validated against injected ground truth (`docs/SPEC.md` Section 4, `docs/ARCHITECTURE.md` Section 1.4).

---

## The dashboard

`dashboard/index.html` — standalone with replay data, or live against `src/api.py`.

- **Consumer / Merchant / Razorpay / Fraud queue** — four lenses on the same transactions
- **Live Simulation** — run a real transaction through the full loop, or carry one through from the checkout demo and see it consistently across every tab
- **Decision Trace** — the exact gating steps for any transaction, using the same constants `pipeline.py` uses
- **Threshold Explorer** — drag through every measured threshold value, real precision/recall/cost numbers, live
- **Under the hood** — tests, detector results, calibration, fairness, and model comparisons, each labeled with its real data source
- **Fraud queue** — pattern narrative and a live feedback loop comparing original predictions against real, human-confirmed outcomes

## Demo flow

`demo/landing.html` -> `demo/checkout.html` (a real human intent goes to a shopping agent, which proposes a purchase, which RiskGate scores live) -> `dashboard/index.html`, with that exact transaction carried through.

---

## Business context

Razorpay already owns Thirdwatch — a mature fraud/RTO product built, as far as can be verified from public description, for a human making the purchasing decision. RiskGate is a new signal category designed to feed into infrastructure like Thirdwatch, not replace it. What RiskGate does and does not claim to solve — including the explicit boundary around agent identity/authentication security and the current conflation of authorization scope with stated intent — is specified precisely in `docs/SPEC.md` Section 9, and argued in `docs/ARCHITECTURE.md` Section 1.

---

## Project structure

```
src/            Core pipeline, models, detectors, API, all analysis scripts
tests/          39 tests - unit + integration
dashboard/      Standalone dashboard (works with or without a live API)
demo/           Checkout + landing page demo flow
docs/           SPEC.md, ARCHITECTURE.md, DECISION_LOG.md, citations, experiment writeups
models/         Trained model artifacts (auto-retrained if load fails)
data/           Synthetic training data + real-data validation results
```

---

## Citations

See `docs/citations.md` for the specific papers behind XGBoost, SHAP, Platt/isotonic calibration, and empirical-Bayes shrinkage, plus industry references (Stripe, MaxMind) informing the fraud-signal design.

---

For a long time, the moment before a payment went through belonged to a
person - a thumb over a PIN pad, a half-second of "wait, do I actually
want this." Agentic commerce is quietly removing that moment, and most of
the infrastructure racing to support it is focused on making the payment
faster, not on asking what got lost when the human pause disappeared.
RiskGate is our answer to that question, not a bigger fraud model, but a
system built to notice the specific, human kind of mistake a machine can
make in good faith. We tried to hold ourselves to the same standard we'd
want a system like this to be judged by: report the real number, not the
flattering one; say what we don't know as plainly as what we do; and
treat every bug we found as something worth explaining, not hiding. If
there is a version of rigor that still has some feeling in it, that's
what we were reaching for.
