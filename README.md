# RiskGate

[![Tests](https://github.com/Ak09patil/riskgate/actions/workflows/tests.yml/badge.svg)](https://github.com/Ak09patil/riskgate/actions/workflows/tests.yml)

A risk layer for AI-agent-initiated transactions, built for Razorpay's AI Buildathon 2026, Track 2 (AI Risk Manager). This is the complete record of the project — reasoning, numbers, and the full engineering trail — since a five-minute video can't hold everything and this can.

## The principles behind this build

Every decision below follows from four rules, applied the same way whether the decision was about a model, a feature, or a line of UI copy:

1. **Explicit over opaque.** Every score in this system resolves to a small set of printable numbers with a stated reason, not a black-box output. This is the same core idea behind Anthropic's own Constitutional AI approach — a model is more trustworthy when it's guided by written, inspectable principles than by an opaque preference nobody can read back.
2. **Test the claim, don't just assert it.** Every "why we chose X over Y" statement in this project has a script behind it that actually ran the comparison. Reasoning is a starting point here, not a finishing one.
3. **Self-critique, then revise, on a loop.** The single biggest driver of quality in this build wasn't the first version of anything — it was going back and checking each finished piece against its own stated standard (calibration checked, fairness checked, coverage checked), finding the gap, and fixing the actual cause. That loop ran dozens of times.
4. **Disclose the limits as clearly as the strengths.** Every claim in this document has an honesty boundary attached to it. A result with no stated limit isn't a stronger result — it's an unchecked one.

## Model choice

Logistic regression scores the fraud-risk model. That's a deliberate choice, tested against the field, not a default.

`src/full_model_comparison.py` runs it against seven other models — Random Forest, Gradient Boosting, XGBoost, LightGBM, SVM, Naive Bayes, KNN — on identical data, features, and held-out split, with every model getting its own independently-tuned threshold. On raw AUC, Random Forest scores 0.005 higher, a gap smaller than this model's own natural variation from picking a different random seed (measured separately at std 0.025). On F2 — the metric that actually decides where the threshold sits, because a missed fraud costs more than an unnecessary hold — logistic regression is the single best model of everything tested. Two automated tests guard both results independently, so if either stops being true, the build fails rather than the claim quietly going stale.

The reasoning behind the choice, before the test confirmed it: Razorpay's own stated bar is that every money decision needs to be explainable and bounded. A model whose entire decision is nine numbers you can print satisfies that more directly than one that needs SHAP values bolted on afterward. Then I tested whether that choice was costing anything — it wasn't.

This holds at the current data size, around 4,000 transactions, and I'm stating that scope directly rather than letting it be assumed to hold at any size. More data generally gives a more flexible model more signal to work with, so this is a staged decision, not a permanent one — and the comparison script isn't a one-off; it's a permanent test that reruns this exact question and fails the build the moment a more complex model actually starts winning.

## The problem

Razorpay is already piloting AI agents that check out on a customer's behalf — Agent Studio, and the NPCI UAP pilot with Zomato, Swiggy, and Zepto. Every payment before this had one moment — a human typing a PIN — that did two jobs at once: it stopped fraud, and it caught honest mistakes, because the person looked once more at what they were about to buy before confirming it. Agentic checkout removes that moment completely. Fraud detection still exists — Razorpay has Thirdwatch, analyzing 200+ signals. That's job one, solved. Nobody's solving job two: catching a fully-authorized, non-malicious agent that still got the purchase wrong.

That gap — agent decision-quality risk — is what RiskGate targets. Not a second fraud detector. A signal category that Thirdwatch's architecture, built for a world where a human always made the final call, was never designed to see.

Thirdwatch's publicly described signal set (device fingerprinting, address quality, buyer behavior) reads as built for a human making the decision — worth stating as an inference from what's public, not verified knowledge of its real feature set. If Thirdwatch already covers this, the framing would need revising. The underlying question doesn't change either way: does any existing fraud system have a concept of agent authorization scope, distinct from fraud? Publicly, nothing suggests one does.

**On staying strictly defense-only:** nothing here performs or enables an attack. The scoring models classify risk, the shopping agent is a benign test harness, and the one LLM use only summarizes already-computed facts. This repo does publish exact model weights and thresholds — worth addressing directly, since it's in service of the interpretability argument above. Those numbers come from a model trained on synthetic, self-generated data; they reveal nothing about Razorpay's real thresholds or Thirdwatch's actual signals. Being transparent about a prototype isn't the same as publishing detail about a real deployed system.

## What it is

Three separate scores on every transaction:

- **Fraud-risk** — is this a bad actor.
- **Intent-match** — did the agent's purchase match what the customer asked for. Kept separate from fraud-risk on purpose: a bad actor needs blocking, an honest mistake needs a quick human check, and one number can't hold both responses at once.
- **Preference-fit** — does this deviation match what this customer has done before. Kept as an honest heuristic, not a third trained model, because there's no ground-truth label anywhere for "would this customer have preferred this" — training against a label I invented myself would be false rigor. Tested directly rather than assumed to work (see "What broke").

These feed a gate with four outcomes: auto-approve, hold for a fraud analyst, hold for a quick customer confirmation, or hold as a likely mistake. 39% of transactions get zero human involvement — the PIN replaced, not simulated. Only 19% go back to the customer, and only for genuinely ambiguous cases; the rest goes to an analyst. The old PIN asked every time, blind to whether it was needed. This only asks when it is.

A circuit breaker sits alongside the three scores: any order more than roughly twice the largest value ever seen in training holds automatically, regardless of score. I added this after testing an unrealistic four-lakh grocery budget myself and watching it sail through as approved, because training never taught the model that value existed. A model has no real basis for an opinion that far outside what it's learned from.

Two more scores, added later and deliberately:

- **Abuse-ring sentinel** (`src/ring_detector.py`) — fraud-risk and intent-match look at one transaction at a time; a coordinated ring across several accounts is invisible to that. Links transactions sharing a pincode, coming from very new agents, landing in a tight time window, then finds connected clusters with union-find. Tested against fifteen injected rings: 92.3% precision, 100% recall, all fifteen recovered. On data with zero injected rings, false-positive rate was 0.07%.
- **Fraud-spike detector** (`src/spike_detector.py`) — a different kind of math, time-series anomaly detection instead of classification. Flags a time window if its fraud rate is far from the typical bucket's rate, using median and MAD instead of mean and standard deviation, since a real spike would drag a mean-based baseline up too. Tested against four injected spikes: 54.5% precision, 54.5% recall — weaker than the ring detector, from noise in low-count buckets, reported as it is.

The track names four example directions. Fraud-risk carries the weight of this submission — the only score checked against a real external dataset, calibration-audited, fairness-audited, benchmarked against the full field. Intent-match, the ring detector, and the spike detector are genuinely validated too, at a lighter standard, because they're extensions, not three more attempts at the same depth. I didn't build a chargeback responder — no ground-truth "did this evidence packet win the dispute" signal exists anywhere, so it can't be measured with real precision and recall, and I'd rather not build something I can't honestly test.

## Why the other big calls

**Not an LLM for the scoring itself.** A bounded, structured classification problem over a handful of features doesn't need a slower, non-deterministic model with no clean feature-weight explanation. Nine printable numbers satisfy "every money action explainable, bounded, gated" more directly than a prompt.

**The one place an LLM is used.** `src/pattern_narrative.py` phrases already-computed, deterministic findings into a readable brief for a fraud analyst — never decides anything. Detection is plain groupby logic, auditable without an API call. No key configured, no problem: the same facts get a clean template instead.

**Why the shopping agent is simple, not agentic.** A multi-agent system and an LLM-driven negotiating agent were both considered and cut. Multi-agent orchestration adds real debugging surface to a part of the system that isn't the actual submission. The negotiating agent was cut for a sharper reason: it would have made RiskGate behave like a merchandising nudge, which sits oddly against Razorpay's public identity as neutral infrastructure, not a recommendation business.

**On building this with heavy AI assistance.** Stated plainly, not apologetically — the track's own criteria name "AI Judgment" as something to evaluate, which only makes sense if AI-assisted building is the expected mode. What's being judged is the decisions on this page: what to build, what to cut, which claims to test instead of assert, which limits to name instead of hide.

## The numbers

- Fraud-risk model: cross-validated AUC around 0.72, stable across five seeds (std ~0.02), F2 around 0.70.
- A hand-written rule ("COD and device mismatch and new agent") scores F2 0.045 on the same data. The trained model beats it by roughly 15x.
- Validated against 284,807 real credit card transactions with real fraud labels, since I don't have real Razorpay data. AUC: 0.972.
- The model was overconfident before I checked — a "0.5–0.6" prediction was right about a third of the time. Fixed with Platt scaling; Brier score moved from roughly 0.22 to roughly 0.19.
- Checked geographic fairness across pincodes. Found one outlier flagging honest customers at 2.8x its actual risk, traced to noisy small-sample rate estimates, fixed with statistical shrinkage — down to 2.42x, with the spread across every pincode tightening, not just the one worst case.
- False-positive rate at the F2-optimal threshold is high, around 85% — indefensible at real volume, which is why the live product gates at a separate, business-realistic threshold (0.5) instead. Both numbers are labeled everywhere so neither is presented as the other.
- 36 automated tests, two tiers, running on GitHub's own servers on every push.
- Translated the model's precision and recall into money, transparently — every assumption stated, none hidden in a formula (`src/cost_sensitivity.py`). At the live threshold and this project's own real order values, fraud loss prevented outweighs revenue put at risk by false holds at every threshold tested, and the gap holds directionally regardless of the exact illustrative volume or abandonment-rate assumption used, because a caught fraud is a full order value while a false hold is a small fraction of one.
- Load-tested the scoring path itself against real concurrent HTTP requests, not claimed a number (`src/load_test.py`): sustained ~220 requests/second with zero errors at 1,000 requests and 50 concurrent connections, on a single unoptimized process. This tests something specific and honest — whether the architecture holds up under real load — not model accuracy at real volume, which needs real data this project doesn't have.

## What broke, and what I did about it

Good numbers alone don't prove much — a model can happen to work. What's harder to fake is a real trail of things that were wrong, found by running the system, not by reading the code and assuming it was fine.

**Data leaked between train and test.** A pincode-rate feature was computed from the full dataset, test rows included. Fixed by computing it train-only, saved as its own artifact.

**The gating logic existed in two places.** `gating.py` had grown into a second, independent copy of the logic already in `pipeline.py`. A threshold change updated one and silently left the other stale — a real bug I hit. Fixed by making `gating.py` a thin wrapper around one implementation. Found the same staleness pattern a third time later, elsewhere, and fixed it the same way.

**Preference-fit had zero real relationship with actual outcomes.** Tested the correlation directly instead of trusting the formula — it was essentially zero, because the deviation signal and the mismatch label had been generated independently. Fixed by wiring a real causal link, then verified it (18% mismatch rate for low preference-fit versus 9.5% for high).

**Cross-platform numerical instability.** Training threw a silent overflow warning on a second machine that never appeared in the original environment. Fixed with stronger regularization, then found the identical warning quietly present in four more files calling the same model, fixed there too.

**`order_id` wasn't reproducible across runs**, generated with a random UUID instead of something deterministic, breaking a feedback feature that depends on looking an order back up later. The fix itself had a second bug — pandas read the new sequential ID as an integer and stripped the leading zeros. Fixed with a non-numeric prefix pandas can't misread.

**Six files each hardcoded their own copy of the fraud feature list**, found only because adding one new feature required updating one copy and revealed the other five never got it. Fixed by having every file import from one place. Found the identical pattern again later, in eight files independently recomputing a pincode rate, fixed the same way.

**Two live endpoints crashed on bad input** — one on an empty request body, one on a non-numeric budget field from a live browser input. Found during a deliberate malformed-input pass. Fixed with real validation on both.

**The fraud queue's approve and reject buttons had no double-click protection**, found in the same pass, fixed with the disable-while-pending pattern already used elsewhere.

**A broken JavaScript comment silently killed the dashboard's interactivity.** A missing `//` meant a whole block was being read as executable code. Found because a real click did nothing, not by any file-level check. Fixed, and I added a real syntax check to my process afterward instead of the weaker one I'd been relying on.

**Two "hold" decisions behaved identically**, both finalizing the order first and explaining afterward — meaning "confirmation" wasn't confirming anything. Found by asking myself directly why two outcomes existed if neither let the customer actually decide. Fixed with a real pre-purchase gate; `HOLD_FRAUD_REVIEW` kept deliberately different, since a fraud hold shouldn't be self-clearable by the customer.

**A concurrency bug in feedback-recording**: five people confirming an outcome at close to the same moment lost four of five records silently, while the system reported success to all five. The first fix passed twenty times in my own environment, then failed differently on separate hardware. The second fix — checking the file's actual size from the OS instead of a buffered stream position — was verified thirty times on the machine that broke the first attempt, then at a hundred simultaneous real HTTP requests.

**Negative and zero prices were silently accepted and scored**, one case even auto-approved, found during a deliberate adversarial-input pass. Fixed with validation on both affected endpoints. A related gap: calling the shopping agent's function directly, bypassing the API, had zero protection against the same input. Fixed at the function itself.

**XGBoost's Python package installs cleanly but its compiled internals need a system library macOS doesn't ship by default.** A comparison script that worked in my environment crashed the moment it ran elsewhere — my error handling only accounted for the package being missing, not present-but-failing-to-load. Fixed by broadening the exception handling to the real failure type, and changing the test to check an actual return value instead of a shallower import check.

**A committed model artifact was trained with a different scikit-learn version than a fresh install pulls by default**, found by cloning the actual public repo fresh — the way anyone judging this would actually experience it. Harmless here, but fixed by pinning the dependency so a fresh install can't silently drift.

**Watching my own demo, I caught a UI message that was simply wrong** — the checkout screen labeled a purchase "within budget" even when the agent had picked something over budget because nothing else matched. Also caught a flow asking the customer to confirm before seeing any risk information at all, with the real reasoning only shown afterward. Fixed both.

Nearly every one of these was found by actually running the system, questioning an assumption, or trying to extend it — not by static review. Confidence has to come from running something repeatedly, in conditions you don't fully control.

## What I know is still missing

Every UX decision — the wording of confirmation screens, whether "propose, then ask" is the right response to a borderline case — was reasoned from my own judgment, never tested against a real person. Proper UX validation needs real users, and a solo submission on this timeline doesn't have that.

Every synthetic-data claim carries that limitation directly, which is exactly why the real-data validation exists — to check the same method against something that isn't mine.

True cross-browser testing wasn't performed; every manual check was done in Safari. The JavaScript used should be safe on any current browser, but that's reasoned confidence, not verified confidence.

## What I'd build next

- Replace synthetic fraud data with real dispute and return outcomes, re-derive both models empirically.
- Integrate real agent-authorization scope objects (UAP or AP2-style mandates) instead of conflating authorization with stated intent.
- Run RiskGate in shadow mode against Thirdwatch's real traffic before trusting any autonomous gating.
- Build a chargeback-evidence responder — deliberately not built here, since it can't be measured with real precision and recall the way everything else in this project was.

## Running it

```
pip install -r requirements.txt
python3 src/generate_data.py
python3 src/train_fraud_model.py
python3 src/train_intent_model.py
python3 src/gating.py
python3 src/build_dashboard_data.py
python3 src/embed_dashboard_data.py
python3 src/api.py          # live API on localhost:5050
```

Open `dashboard/index.html` for the operator view, or `demo/checkout.html` for the consumer flow. Both work standalone from sample data and switch to live scoring the moment `src/api.py` is running.

Every validation script mentioned above, runnable directly:

```
python3 src/seed_validation.py
python3 src/drift_test.py
python3 src/baseline_comparison.py
python3 src/real_data_validation.py
python3 src/calibration_check.py
python3 src/fairness_check.py
python3 src/cost_sensitivity.py
python3 src/load_test.py       # needs src/api.py running first — real throughput/latency numbers
python3 src/model_complexity_comparison.py
python3 src/full_model_comparison.py
python3 src/ring_detector.py
python3 src/spike_detector.py
```

Full test suite: `pytest tests/ -v`

`docs/ARCHITECTURE.md` structures this same reasoning against the buildathon's own four judging criteria. `TESTING.md` has the complete, unfiltered bug log.
