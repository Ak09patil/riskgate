# RiskGate — Architecture Documentation

Submitted for: **AI Buildathon, Track 2 (AI Risk Manager)**

This document is structured around the four criteria stated in the buildathon brief — Problem Taste, Build Quality, AI Judgment, Failure Recovery — each answered explicitly rather than left to be inferred from the code. For the system's precise contract (data schema, gating logic as a formal specification, evaluation methodology), see `docs/SPEC.md`. For the full chronological engineering narrative, see `docs/DECISION_LOG.md`.

---

## Executive summary

| Criterion | Evidence |
|---|---|
| Problem Taste | Targets **agent decision-quality risk** — a category distinct from fraud, unaddressed by existing infrastructure — not a generic fraud detector |
| Build Quality | Calibrated XGBoost, F2 = 0.653 vs. a naive rule's 0.045 (14.5x); 39 automated tests; fairness and calibration audited and fixed, not just measured |
| AI Judgment | Migrated from logistic regression to XGBoost on real-data evidence (F2 0.8557 vs 0.7073), not a synthetic-data artifact; LLM used exactly once, for phrasing only, never for a decision |
| Failure Recovery | Eight distinct, real failure classes found and fixed, several only surfaced by testing on machines and platforms beyond the original development environment |

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

Every arrow above is a real, running code path. `src/api.py` exposes the pipeline over HTTP; `dashboard/index.html` and `demo/checkout.html` are two live consumers of it.

---

## 1. Problem Taste

### 1.1 The gap: authorization is not risk

The literal Track 2 brief asks for a detector/verifier for one class of loss. The obvious read is "build a fraud model." That read misses where the actual new risk in agentic commerce sits.

Authorization and risk are two different questions, and conflating them is the mistake worth naming explicitly:

| Question | Type | When answered | How |
|---|---|---|---|
| "Is this agent allowed to spend up to Rs 2,000 at this merchant?" | Authorization | Once, upfront | A rule check — ideally a cryptographically-scoped mandate (the direction UAP and AP2-style protocols are converging on: one-time consent with hard limits, not a PIN prompt per transaction) |
| "Given this agent IS authorized, is THIS transaction likely a mistake, a scam, or a probable loss?" | Risk | Per transaction | Judgment, not a rule check |

RiskGate is built entirely in the second lane. It assumes the authorization question has already been answered correctly upstream, and evaluates risk *given* that authorization holds.

**Why that boundary matters:** an agent's identity itself can be spoofed or manipulated — a compromised credential, a malicious product listing engineering a prompt injection. That is a real threat, and it is a security/identity problem, not a risk-scoring problem. RiskGate does not claim to solve it. What it distinguishes is "this transaction looks statistically unusual" (RiskGate's job) from "this agent's authorization itself might be compromised" (a different system's job, upstream of RiskGate). Naming this boundary is itself part of the engineering judgment being demonstrated — a system that quietly claimed to cover both would be overclaiming.

### 1.2 The new failure mode: agent decision-quality risk

Every risk system Razorpay runs today — and every direction named in Track 2 itself — is built to catch bad actors: fraud, chargebacks, abuse. That is "is this person trying to cheat us." Agentic commerce introduces a failure mode outside that frame entirely: an agent can be fully authorized, fully non-malicious, acting in complete good faith, and still cause a return or dispute because it misjudged intent — wrong size, optimized for "cheapest under Rs 6,000" when the human cared about brand, matched a catalog listing that looked right but wasn't. The merchant eats the same loss either way.

This is a genuinely new category — **agent decision-quality risk**, not fraud risk. Current fraud infrastructure has never had to distinguish these, because until agentic checkout, a human was always there confirming in the moment. That confirmation step is precisely what agentic checkout removes, and precisely what a single fraud score does not replace.

### 1.3 Asymmetric stakes

A real solution has to be explicit about which error it is biased to avoid, not just report both numbers. Wrongly blocking a legitimate agent transaction costs the merchant a sale and annoys a customer. Wrongly approving a bad one costs money and trust — and at scale, could shake confidence in agentic commerce itself, right as NPCI and Razorpay are trying to prove it is safe enough to scale nationally.

That tension is not abstract — it is the concern behind NPCI's own framing: "how do we control a machine going rogue? We need all parties having that information if something goes wrong." RiskGate's two-tier threshold (Sec 2) is the concrete answer to that asymmetry: recall is prioritized over precision at the production threshold, deliberately, because a missed fraud costs the full order value while an unnecessary quick-verify step costs only friction. That choice is stated and defended, not left implicit in a single undifferentiated score.

### 1.4 Scope of the build

One primary build, at real depth, plus three genuine, validated extensions — not a checklist. Fraud-risk carries the depth of this submission: the only component validated against a real external dataset (Kaggle Credit Card Fraud, 284,807 real transactions — see Sec 3.1), the only one checked for calibration, the only one audited for geographic fairness with a proper statistical test (bootstrap confidence intervals, not a raw ratio), and the only one benchmarked against both a naive rule and seven alternative model architectures.

Intent-match, the abuse-ring sentinel, and the fraud-spike detector are genuine, working, separately-validated capabilities — each with its own held-out precision/recall against real injected ground truth — but they are extensions built on top of the core work, not three more attempts at the same depth.

### 1.5 Positioning against existing infrastructure

Razorpay owns Thirdwatch (acquired 2019) — a mature fraud/RTO product analyzing 200+ signals with merchant-configurable thresholds. Its publicly described signal set reads as built for a *human* making the purchasing decision. This is an inference from Thirdwatch's public description, not verified internal knowledge, and would need revising if Thirdwatch already has an agent-context signal not publicly documented. RiskGate is built as a new signal category designed to feed into infrastructure like Thirdwatch, not replace it — per-merchant threshold customization, which Thirdwatch already does well, is exactly the kind of capability RiskGate should compose with, not duplicate.

**On "strictly defense-only":** nothing in this submission performs or enables an attack. This repo publishes exact model weights and thresholds, trained on **synthetic, self-generated data** — they reveal nothing about Razorpay's real production thresholds or Thirdwatch's actual signals.

---

## 2. Build Quality

### 2.1 Models

| Score | Model | Validation |
|---|---|---|
| Fraud-risk | Calibrated XGBoost (migrated from an initial logistic regression build — Sec 3.1) | Train/test split, 5-fold CV, F2-scanned two-tier thresholds, Platt calibration, no data leakage |
| Intent-match | Logistic regression | Same rigor as fraud-risk |
| Preference-fit | Explicit heuristic formula, not a trained model | Explicitly labeled lighter-weight — no clean ground-truth label exists for "would this customer have preferred this" |

Preference-fit's scope is narrow by design: not to help a customer spend more happily (a merchandising function, outside Razorpay's lane), but to give the risk gate more context than budget-adherence alone when deciding whether a deviation is a probable mistake or a welcome one.

### 2.2 Benchmarked against a baseline

A naive rule ("flag if COD AND device mismatch AND new agent") scores **F2 = 0.045** on held-out data. The trained model scores **F2 = 0.653** on the identical set — **14.5x better**. This is the evidence the model earns its complexity rather than being complexity for its own sake.

### 2.3 System integrity

One unified `score_transaction()` function that every component calls — the shopping agent, batch scoring, the live API, both frontends. No separate batch/live implementation to drift apart.

### 2.4 Automated testing

**39 tests** across unit and integration tiers: the scoring pipeline, the shopping agent, the bounded trust override's exact conditions, regression guards on both detectors and on model quality itself, and a real concurrent-write regression test (30 simultaneous threads hitting `/record_outcome`, verified not to lose data on either platform tested).

### 2.5 Gaps found and closed, not just reported

| Gap | Finding | Fix | Verified result |
|---|---|---|---|
| Calibration | Raw XGBoost overconfident — a "0.9" prediction was only actually fraud ~69% of the time | Platt scaling | Brier score 0.229 -> 0.194 |
| Fairness | Worst-case pincode disparity 3.44x at production threshold | Empirical-Bayes shrinkage + bootstrap 95% CI, not just the raw ratio | CI width ~0.31 — not statistically distinguishable from sampling noise at current volume |

At threshold 0.20, the same fairness check gives a materially narrower CI (~0.16) — that disparity *would* be a confirmed, real bias, which is part of why 0.20 was rejected as the production threshold despite being F2-optimal.

### 2.6 Honest, quantified limits that remain

- The F2-optimal threshold on this data is 0.20, not 0.25. Not used in production: the resulting flag rate exceeds 85% in some pincodes — blanket friction, not targeted risk-based friction. The production system gates at a two-tier 0.25/0.45 split instead.
- The synthetic fraud-probability formula's coefficients are grounded in cited, general fraud indicators, not empirically calibrated against real Razorpay data, which we do not have access to.

---

## 3. AI Judgment

### 3.1 The model migration: logistic regression -> XGBoost

The first working, fully-validated version of this project used logistic regression for fraud-risk — a reasoned choice at the time: a bounded, structured classification problem where an interpretable linear decision boundary is easier to satisfy "every money action explainable, bounded and gated" with than an opaque model.

That choice was validated twice, against two different kinds of data, with two different results:

| Validation | Dataset | Result |
|---|---|---|
| Synthetic (`full_model_comparison.py`) | Our own generated data, 8 models compared | All models cluster within normal seed-to-seed noise (AUC spread 0.662-0.701, seed variance std 0.025) — no architecture stands out |
| Real (`held_out_validation.py`) | Kaggle Credit Card Fraud, 284,807 real transactions | **XGBoost F2 = 0.8557 vs. logistic regression's 0.7073** — a real, large gap, not noise |

Read alone, the synthetic result would have kept the project on logistic regression indefinitely. Real fraud has non-linear feature interactions a linear model structurally cannot capture; the synthetic generator produces signal as an additive combination of features (deliberately, for auditable ground truth), which a linear model fits well and real fraud does not share.

**The honest reading of both results together:** the project's own synthetic benchmark would have misled the architecture decision. That is specifically why we did not rely on it alone. The entire production pipeline was migrated on the strength of the real-data result — retrained from scratch with Platt calibration built in, every downstream threshold recalibrated against the new model's actual score distribution, and every validation script re-run against the new model rather than assuming old results still applied. The two-tier threshold design (Sec 2.6) is itself a product of this migration.

### 3.2 Why the shopping agent is rule-based, not agentic

A CrewAI-style multi-agent system, and an LLM-driven negotiating agent, were both considered and cut. Multi-agent orchestration adds real debugging surface for a part of the system that is not the actual submission. The negotiation idea was cut for a sharper reason: it would have made RiskGate function as a merchandising nudge, sitting uneasily against Razorpay's public positioning as neutral payments infrastructure.

### 3.3 Why preference-fit is a heuristic, not a third trained model

There is no clean historical label for "would this customer have preferred this deviation" — training a model against a fabricated label would be false rigor. An explicit, transparent formula, labeled as such, is more honest than hiding an equally-uncertain guess behind a model's apparent authority.

### 3.4 Why three scores instead of one

Collapsing fraud-risk and intent-match into a single number would hide the distinction that actually matters operationally: a bad actor should be blocked; an honest agent's mistake should get a quick human nod. A single score cannot express that difference.

### 3.5 Where an LLM is actually used

`pattern_narrative.py` uses an LLM exactly once in the whole system, and deliberately not for a decision: it phrases already-computed, deterministic findings into a short brief for a fraud analyst. The detection itself never touches the LLM — plain, auditable groupby logic. If no API key is configured, the same facts are phrased with a clean template instead.

---

## 4. Failure Recovery

The buildathon's own language asks for evidence of "what broke at 2am, and how you got out." The honest answer is not one bug — it is a *pattern* of the same class of bug, found repeatedly by increasing scrutiny, traced to a structural cause, fixed at the root each time.

| # | Category | What broke | Fix |
|---|---|---|---|
| 1 | Data leakage | An early fraud model computed its pincode-risk feature from the full dataset, including test rows | Computed train-only, saved as its own artifact |
| 2 | Architecture | `gating.py` was a second, independent copy of `pipeline.py`'s logic — a threshold change silently went stale in one copy but not the other | `gating.py` made a thin wrapper around `pipeline.py` |
| 3 | Data generation | Preference-fit was designed to predict real outcomes, but direct correlation testing showed essentially zero relationship (-0.013) with actual mismatch labels, generated independently | Wired a real causal link, verified afterward |
| 4 | Design flaw | Two "hold" decisions both finalized the checkout order regardless, then explained it after the fact | Added a real pre-purchase confirmation gate |
| 5 | Model boundary | A Rs 4,00,000 order with clean signals auto-approved — nothing that large exists in training data | Circuit breaker added; verified as the only thing catching this case, via regression test |
| 6 | Cross-platform (threading) | `fcntl.flock()` is Unix-only, hard-crashes on Windows; even after fixing with `msvcrt.locking()`, a concurrent-write test still lost data on Windows specifically, because `locking()` does not reliably block a second file handle opened by the same process | Branched on `os.name`; added a Python-level `threading.Lock()` on every platform |
| 7 | Cross-platform (serialization) | A model trained on macOS failed to load on Windows (`input stream corrupted`) — confirmed identical file bytes and XGBoost versions on both machines, ruling out corruption or a version mismatch | `pipeline.py` now catches this and retrains locally, automatically, once |
| 8 | Dependencies | `requirements.txt` was missing two real dependencies (`shap`, `requests`) actually imported by two of our own scripts | Added, verified with a fresh install |

The common thread: nearly every one of these was found by *someone actually running the system on a machine or in a condition not already tested* — not by static review alone.

See `docs/DECISION_LOG.md` for the full chronological engineering narrative.

---

## What we'd build next, if this continued

- Replace synthetic fraud data with real dispute/return outcomes, and re-derive the model empirically rather than from stated priors.
- Integrate with real agent-authorization scope objects (UAP/AP2-style mandates) instead of conflating authorization with stated intent, as this prototype currently does — see `docs/SPEC.md` Sec 9.
- Run RiskGate in shadow mode against real traffic to validate precision/recall before autonomous gating is trusted — `feedback_loop.py` is a working, minimal version of exactly this mechanism.
- True online/continual learning is a materially harder, riskier problem (concept drift, catastrophic forgetting, no clean real-time validation) — not attempted here; the shadow-mode feedback loop is the right-sized first step toward it.
