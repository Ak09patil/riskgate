# RiskGate - Architecture Documentation

Submitted for: **AI Buildathon, Track 2 (AI Risk Manager)**
This document is structured around the four criteria stated in the buildathon brief - Problem Taste, Build Quality, AI Judgment, Failure Recovery. 

---

## System diagram

```
                    HUMAN INTENT
              (category, budget, attribute)
                          |
                          v
              +-----------------------+
              |   SHOPPING AGENT       |   src/shopping_agent.py
              |   (rule-based matcher, |   Test harness only --
              |   NOT the submission)  |   proves RiskGate against
              +-----------+-----------+   a realistic scenario
                          |
                proposed purchase
                          |
                          v
    +-------------------------------------------------+
    |              RISKGATE PIPELINE                    |   src/pipeline.py
    |         (score_transaction -- ONE entrypoint)      |   THE submission
    |                                                     |
    |   +-----------+ +-----------+ +-------------+     |
    |   | Fraud-risk | |  Intent-   | | Preference- |     |
    |   |  (calibrated| |  match     | | fit         |     |
    |   |  XGBoost,  | |  (trained, | | (heuristic, |     |
    |   |  validated)| |  validated)| | labeled as  |     |
    |   |            | |            | | such)       |     |
    |   +-----+------+ +-----+------+ +------+------+     |
    |         +--------------+---------------+            |
    |                        v                             |
    |         +----------------------------+                |
    |         |  GATING LOGIC (two-tier)    |                |
    |         |  circuit breaker ->         |                |
    |         |  0.45 fraud floor ->        |                |
    |         |  0.25 ambiguous band +      |                |
    |         |  bounded trust override ->  |                |
    |         |  intent-match -> pref-fit   |                |
    |         +----------------------------+                |
    +------------------------+--------------------------+
                              |
        +---------+----------+---------+---------+----------+
        v         v          v         v         v          v
  AUTO_APPROVE  HOLD_QUICK  HOLD_FRAUD  HOLD_CONFIRM  HOLD_LIKELY_
                _VERIFY     _REVIEW     _WITH_HUMAN   MISMATCH
```

Every arrow in this diagram is a real, running code path. `src/api.py` exposes the pipeline over HTTP; `dashboard/index.html` and `demo/checkout.html` are two live consumers of it.

---

## 1. Problem Taste


**The literal Track 2 brief asks for a detector/verifier for one class of loss.** The obvious read is "build a fraud model." That read misses where the actual new risk in agentic commerce sits.

**Authorization is not risk.** These are two different questions, and conflating them is the mistake worth naming explicitly. "Is this agent allowed to spend up to ₹2,000 at this merchant?" is an authorization
question - checked once, upfront, enforced automatically, ideally via a cryptographically-scoped mandate (the direction UAP and AP2-style protocols are converging on: one-time consent with hard limits, rather
than a PIN prompt on every transaction). "Given this agent IS authorized, is THIS particular transaction likely to be a mistake, a scam, or something that causes a return, dispute, or loss?" is a risk question - 
and answering it needs judgment, not a rule check. RiskGate is built entirely in that second lane. It assumes the authorization question has already been answered correctly upstream, and evaluates risk *given* that authorization holds.

**Why that boundary matters** an agent's identity itself can be spoofed or manipulated - a compromised credential, a malicious
product listing engineering a prompt injection. That's a real threat, and
it's a security/identity problem, not a risk-scoring problem. RiskGate
does not claim to solve it. What it distinguishes is "this transaction
looks statistically unusual" (our job) from "this agent's authorization
itself might be compromised" (a different system's job, upstream of us).
Naming this boundary is itself part of the engineering judgment being
demonstrated here - a system that quietly claimed to cover both would be
overclaiming.

**Inside the risk lane, agentic commerce introduces a genuinely new failure mode.** Every risk system Razorpay runs today - and every direction named in Track 2 itself - is built to catch bad actors: fraud, chargebacks, abuse. That's "is this person trying to cheat us." However, a gap identifies here is that an
agent can be fully authorized, fully non-malicious, acting in complete good faith, and still cause a return or dispute wave because it misjudged intent: wrong size, optimized for "cheapest under ₹6,000" when the human actually cared about brand, matched a catalog listing that
looked right but wasn't. Nobody did anything wrong, and the merchant eats the loss exactly as if it were fraud. This is a genuinely new category — **agent decision-quality risk** - not "fraud risk." Current fraud infrastructure has never had to distinguish these, because until agentic
checkout, a human was always there confirming in the moment. That confirmation step is precisely what agentic checkout removes, and precisely what a single fraud score does not replace.

**The stakes here are asymmetric, and a real solution has to be explicit about which error it's biased to avoid, not just report both numbers.** Wrongly blocking a legitimate agent transaction costs the merchant a sale and annoys a customer. Wrongly approving a bad one costs money and trust
 and at scale, could shake confidence in agentic commerce itself, right when NPCI and Razorpay are trying to prove it's safe enough to scale nationally. That tension is not abstract: it's the exact concern behind NPCI's own framing of the problem — "how do we control a machine going
rogue? We need all parties having that information if something goes wrong." RiskGate's two-tier threshold (see Build Quality) is the concrete answer to that asymmetry: recall is prioritized over precision at the production threshold, deliberately, because a missed fraud costs the full
order value while an unnecessary quick-verify step costs only friction and that choice is stated and defended, not left implicit in a single undifferentiated score.

**One primary build, at real depth, plus three genuine, validated
extensions not a checklist.** Fraud-risk is where the actual depth of
this submission lives: the only component validated against a real,
external dataset (Kaggle Credit Card Fraud, 284,807 real transactions
see AI Judgment for the migration story this drove), the only one
checked for calibration, the only one audited for geographic fairness
with a proper statistical test (bootstrap confidence intervals, not a
raw ratio), and the only one benchmarked against both a naive rule and
seven materially different model architectures. Intent-match, the
abuse-ring sentinel, and the fraud-spike detector are genuine, working,
separately-validated capabilities each with its own held-out
precision/recall against real injected ground truth but they're
extensions built on top of the core work, not three more attempts at the
same depth.

**Why this isn't redundant with what Razorpay already has:** Razorpay
owns Thirdwatch (acquired 2019) - a mature fraud/RTO product analyzing
200+ signals with merchant-configurable thresholds. Its publicly
described signal set reads as built for a *human* making the purchasing
decision - this is an inference from Thirdwatch's public description,
not verified internal knowledge, and would need revising if Thirdwatch
already has an agent-context signal we're not aware of. RiskGate is built
as a new signal category designed to feed into infrastructure like
Thirdwatch, not replace it - per-merchant threshold customization (which
Thirdwatch already does well) is exactly the kind of capability RiskGate
should compose with, not duplicate.

**On "strictly defense-only":** nothing in this submission performs or
enables an attack. This repo publishes exact model weights and
thresholds, trained on **synthetic, self-generated data** they reveal
nothing about Razorpay's real production thresholds or Thirdwatch's
actual signals.

---

## 2. Build Quality

**Two independently validated models, one honest heuristic:**
- Fraud-risk: calibrated XGBoost (migrated from an initial logistic regression build - see AI Judgment for why), proper train/test split, 5-fold cross-validation, F2-scanned two-tier thresholds, Platt-calibrated, no data leakage (pincode-rate and pincode-ring-rate lookups computed train-only, saved as their own artifacts).
- Intent-match: logistic regression, same rigor.
- Preference-fit: explicitly labeled a heuristic, not oversold as statistically validated. Its job is narrowly scoped: not to help a customer spend more happily (a merchandising function, outside Razorpay's lane), but to give the risk gate more context than budget-adherence alone when deciding whether a deviation is a probable mistake or a welcome one.

**Proven against a baseline:** a naive rule ("flag if COD AND device mismatch AND new agent") scores **F2 = 0.045** on held-out data. The trained model scores **F2 = 0.653** on the identical set — 14.5x better.

**Real end-to-end system, not a notebook:** one unified `score_transaction()` function that every other component calls.

**Automated testing:** **39 tests** across unit and integration tiers, including the bounded trust override's exact conditions, regression guards on both detectors and on model quality itself, and a real concurrent-write regression test (30 simultaneous threads hitting `/record_outcome`, verified not to lose data).

**We went back and closed our own named gaps:**
- **Calibration**: raw XGBoost was overconfident (a "0.9" prediction was only actually fraud ~69% of the time). Platt scaling fixed this, verified with a real Brier-score improvement (**0.229 -> 0.194**), baked directly into the production training pipeline.
- **Fairness**: at the production threshold (0.25), worst-case pincode disparity is **3.44x** but a bootstrap 95% confidence interval (width ~0.31) shows this is **not statistically distinguishable from sampling noise** at current data volume. At threshold 0.20, the same check gives a much narrower CI (~0.16) — that disparity *would* be a confirmed, real bias, part of why 0.20 was rejected despite being F2-optimal.

**Honest, quantified limits that remain:**
- The F2-optimal threshold on this data is 0.20, not 0.25 we didn't use it, because the flag rate there exceeds 85%, becoming blanket friction on nearly all customers rather than targeted risk-based friction. The production system gates at a two-tier 0.25/0.45 split instead.
- The synthetic fraud-probability formula's coefficients are grounded in cited, general fraud indicators, not empirically calibrated against real Razorpay data, which we don't have.

---

## 3. AI judgement

**On how this was built: 
Note:  this project was built with AI assistance throughout.
**The model migration: why we started with logistic regression, and why we moved to XGBoost.** The first working, fully-validated version of this project used logistic regression for fraud-risk - a reasoned choice: a bounded, structured classification problem where an interpretable linear decision boundary is easier to satisfy "every money action explainable, bounded and gated" with than an opaque model.

We didn't stop at validating that choice against our own synthetic data. `full_model_comparison.py` tests eight models on identical data, features, and methodology. **On our own synthetic data, every model clusters within normal seed-to-seed noise** (AUC spread 0.662-0.701, natural seed variance std 0.025) — no architecture stands out, XGBoost included. Read alone, this would have kept us on logistic regression indefinitely.

But we went further and validated the same model choice against a real, external dataset - `held_out_validation.py` against Kaggle's Credit Card Fraud dataset, 284,807 real transactions. There, the result flips decisively: **XGBoost scores F2 = 0.8557 against logistic regression's 0.7073** — a real, large gap, not noise. Real fraud has non-linear feature interactions a linear model structurally can't capture; our synthetic generator produces signal as an additive combination of features (deliberately, for auditable ground truth), which a linear model fits well and real fraud doesn't share.

**The honest reading of both results together:** our own synthetic benchmark would have misled the architecture decision. That's specifically why we didn't rely on it alone. We migrated the entire production pipeline on the strength of the real-data result: retrained from scratch with Platt calibration built in, recalibrated every downstream threshold against the new model's actual score distribution, and re-ran every validation script against the new model rather than assuming old results still applied. The two-tier threshold design is itself a product of this migration.

**Why the shopping agent is rule-based, not agentic.** A CrewAI-style multi-agent system, and an LLM-driven negotiating agent, were both considered and cut. Multi-agent orchestration adds real debugging surface for a part of the system that isn't the actual submission. The negotiation idea was cut for a sharper reason: it would have made RiskGate function as a merchandising nudge, sitting uneasily against Razorpay's public positioning as neutral payments infrastructure.

**Why preference-fit is a heuristic, not a third trained model.** There is no clean historical label for "would this customer have preferred this deviation" training a model against a fabricated label would be false rigor. Keeping it an explicit, transparent formula is more honest than hiding an equally-uncertain guess behind a model's apparent authority.

**Why three scores instead of one.** Collapsing fraud-risk and intent-match into a single number would hide the distinction that actually matters operationally: a bad actor should be blocked; an honest agent's mistake should get a quick human nod. A single score can't express that difference.

**Where an LLM actually is used.** `pattern_narrative.py` uses an LLM exactly once, and deliberately not for a decision: it phrases already-computed, deterministic findings into a short brief for a fraud analyst. The detection itself never touches the LLM.

---

## 4. Failure Recovery

The buildathon's own language asks for evidence of "what broke at 2am, and how you got out." The honest answer isn't one bug - it's a *pattern* of the same class of bug, found repeatedly by increasing scrutiny, traced to a structural cause, fixed at the root each time:

1. **Data leakage** - an early fraud model computed its pincode-risk feature from the full dataset, including test rows. Fixed by computing it train-only.
2. **A duplicated gating implementation** `gating.py` was a second, independent copy of `pipeline.py`'s logic, which is why a threshold change silently went stale in one copy but not the other. Fixed by making `gating.py` a thin wrapper.
3. **A causal gap in the synthetic data** preference-fit was designed to predict real outcomes, but direct correlation testing showed essentially zero relationship (-0.013) with actual mismatch labels, generated independently. Fixed with a real causal link, verified afterward.
4. **A real design flaw** - two "hold" decisions both used to finalize the checkout order regardless, then explain it after the fact. Fixed by adding a real pre-purchase confirmation gate.
5. **A Rs 4,00,000 order with clean signals auto-approved** nothing that large exists in training data, so the model had no real basis for a score. The circuit breaker is the only thing catching this, verified with a regression test.
6. **Cross-platform, found only by testing on genuinely different machines:** `feedback_loop.py` used `fcntl.flock()` Unix-only, would hard-crash on Windows. Fixed by branching on `os.name`. Even after that fix, a concurrent-write test still lost data on Windows specifically: `locking()` doesn't reliably block a second file handle opened by the same process (a documented Windows CRT limitation), and Flask's dev server handles concurrent requests as threads in one process. Fixed with an additional Python-level `threading.Lock()`.
7. **A model trained on macOS failed to load on Windows** confirmed via testing that file bytes and XGBoost versions were identical on both machines, ruling out corruption or a version mismatch. A genuine cross-machine pickle-portability quirk. `pipeline.py` now catches this and retrains locally, automatically, once.
8. **`requirements.txt` was missing two real dependencies** (`shap`, `requests`) that two of our own scripts actually import.

The common thread: nearly every one of these was found by *someone actually running the system on a machine we hadn't already tested on* not by static review alone.

See `docs/DECISION_LOG.md` for the full chronological engineering narrative.

---

## What we'd build next, if this continued

- Replace synthetic fraud data with real dispute/return outcomes.
- Integrate with real agent-authorization scope objects (UAP/AP2-style mandates) instead of conflating authorization with stated intent, as this prototype currently does - see `docs/SPEC.md`.
- Run RiskGate in shadow mode against real traffic to validate precision/recall before autonomous gating is trusted - `feedback_loop.py` is a working, minimal version of exactly this mechanism.
- True online/continual learning is a materially harder, riskier problem (concept drift, catastrophic forgetting, no clean real-time validation) - not attempted here; the shadow-mode feedback loop is the right-sized first step toward it.
