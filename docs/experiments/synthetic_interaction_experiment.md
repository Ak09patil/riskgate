# Experiment: adding non-linear interactions to the synthetic data generator

**Date:** September 2026
**Motivation:** Our production model (calibrated XGBoost) loses to logistic
regression on our own synthetic training data (AUC ~0.697 vs ~0.655-0.676
across several retrains), even though it wins decisively on real
transaction data (see `held_out_validation_results.csv`: XGBoost F2=0.856
vs logistic regression F2=0.707 on the Kaggle Credit Card Fraud dataset,
284,807 rows). We wanted to know: is this gap because our synthetic data's
fraud-probability formula is purely additive/linear, which structurally
favors a linear model and gives a tree ensemble nothing real to capture?

## What we changed

`generate_data.py`'s fraud-probability formula was, before this
experiment, a strictly additive sum of independent weighted signals (device
mismatch, new agent, COD, pincode rate, high value, spike window) — no
signal's effect depended on any other signal's value. We added two
genuine, non-linear interaction terms, chosen for real-world grounding
(not tuned to hit a target metric, consistent with this project's stated
principle — see `generate_data.py`'s docstring):

1. **`device_ip_consistency == 0 AND agent_age_days < 15`**: +0.20 to
   fraud probability, beyond each factor's individual contribution. A
   brand-new agent account transacting from an inconsistent device/IP is a
   specific, compounding fraud pattern (freshly-created identity + unowned
   device), not just two independent risks.
2. **`payment_mode == "COD" AND order_price > 5000`**: +0.15 beyond each
   factor's individual contribution. High-value COD orders are a
   documented compounding risk in Indian e-commerce — COD removes
   pre-delivery payment verification, and higher value raises the payoff
   for exploiting that gap.

## What we measured

Retrained the fraud model on the new data and re-ran
`model_complexity_comparison.py` (identical train/test split, features,
and methodology as always used for this comparison).

| Model | AUC | F2 |
|---|---|---|
| Logistic Regression (fresh retrain) | 0.722 | 0.719 |
| XGBoost (100 trees, depth 4) | 0.699 | 0.629 |
| XGBoost 5-fold CV AUC | 0.712 (+/- 0.022) | — |

**Logistic regression still won.** The interaction addition did not flip
the overall comparison.

However, XGBoost's own feature-importance output showed
`cod_and_high_value` — a feature engineered in `pipeline.py` specifically
to let the model see this interaction directly — jumped to **0.561, by
far its most important feature**, up from roughly 0.07 before this
change. This confirms the interaction we added is real and genuinely
learnable; XGBoost is demonstrably using it. Logistic regression still
won the overall comparison because most of the remaining signal in the
generator (the majority of the original weighted terms) is still
additive/linear — two interaction terms among roughly eight total signals
was not enough non-linear structure to flip an aggregate AUC comparison
dominated by linear-friendly signal.

**Reproducibility note:** `data/transactions_pre_interactions_backup.csv`
holds the ORIGINAL (pre-interaction) dataset, not the interaction-version
dataset used to produce the numbers above — the interaction-version CSV
itself was overwritten during revert and not preserved separately. The
interaction code change is preserved in git history (the commit that
added it, later reverted) and can be reapplied to regenerate the exact
experimental dataset if needed.

## Decision: reverted

We reverted to the original (pre-interaction) synthetic dataset rather
than keep the new one, because:

- It did not resolve the actual problem it was aimed at (the
  synthetic-vs-real model contradiction remains, in weaker form)
- Artificially strengthening the interaction terms further to force a
  flip would have violated this project's own stated principle that
  generator coefficients are grounded in real-world reasoning chosen
  BEFORE seeing what metric they produce, not tuned post-hoc to hit a
  target result
- Keeping a second dataset version alive would mean maintaining two
  parallel retrain/refairness/recalibration cascades for a change that
  didn't deliver its intended outcome

## What this experiment actually established

Even though the flip didn't happen, this was a genuine, worthwhile test,
not a wasted effort: it demonstrates our production model can learn real
non-linear feature interactions when they exist (confirmed via SHAP/
feature-importance evidence, not just assumed), which directly supports
the case for using tree ensembles once real transaction data is available
in production — where non-linear interactions are known to be far more
prevalent than in our necessarily-simplified synthetic generator.
