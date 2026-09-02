# Citations — for use in README / ARCHITECTURE.md

Curated from a broader research pass. Only sources judged safe to cite
without further verification are included here. Before using, still do
a final spot-check that each link resolves (a few minutes, not skippable
just because a paper is well-known).

## Core technical claims (peer-reviewed, foundational)

**1. Why gradient-boosted trees (XGBoost) for tabular fraud data**
Chen, T., & Guestrin, C. (2016). *XGBoost: A Scalable Tree Boosting
System.* Proceedings of the 22nd ACM SIGKDD International Conference on
Knowledge Discovery and Data Mining (KDD '16).
https://doi.org/10.1145/2939672.2939785

**2. Why SHAP for explainability**
Lundberg, S. M., & Lee, S.-I. (2017). *A Unified Approach to
Interpreting Model Predictions.* Advances in Neural Information
Processing Systems 30 (NeurIPS 2017).
https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html

**3. Why calibration (Platt scaling) matters for tree ensembles**
Niculescu-Mizil, A., & Caruana, R. (2005). *Predicting Good
Probabilities with Supervised Learning.* Proceedings of the 22nd
International Conference on Machine Learning (ICML 2005).
https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf

**4. Why calibration — isotonic regression alternative**
Zadrozny, B., & Elkan, C. (2002). *Transforming Classifier Scores into
Accurate Multiclass Probability Estimates.* Proceedings of the 8th ACM
SIGKDD International Conference on Knowledge Discovery and Data Mining
(KDD 2002). https://doi.org/10.1145/775047.775111

**5. Why empirical-Bayes shrinkage for per-pincode fairness**
Morris, C. N. (1983). *Parametric Empirical Bayes Inference: Theory and
Applications.* Journal of the American Statistical Association, 78(381),
47-55. https://doi.org/10.1080/01621459.1983.10500471
(This is the foundational citation for the exact shrinkage technique
used in compute_shrunk_pincode_rates() / compute_shrunk_pincode_ring_rates().)

## Likely real, worth a quick link-check before citing

**6. LightGBM (for general tree-ensemble context, not directly used but relevant background)**
Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., He, Q., &
Liu, T.-Y. (2017). *LightGBM: A Highly Efficient Gradient Boosting
Decision Tree.* Advances in Neural Information Processing Systems 30
(NeurIPS 2017).
https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html

## Industry practice references (not peer-reviewed, cite as industry sources, not academic ones)

**7. Multi-tier fraud decision thresholds in production systems**
Stripe. *How a Fraud Score Works: A Guide for Businesses.*
https://stripe.com/resources/more/fraud-scores-explained

MaxMind. *Set thresholds for risk scores (minFraud).*
https://support.maxmind.com/knowledge-base/articles/set-thresholds-for-risk-scores-minfraud

**8. COD fraud/RTO risk in Indian e-commerce**
Razorpay. *Cash on Delivery in India: Benefits, Risks & RTO Tips.*
https://razorpay.com/blog/cash-on-delivery/
(Reports 25-30% RTO rate for COD vs 2-3% for prepaid in India — verify
this specific figure is still on the page before quoting it directly.)

## Deliberately NOT cited — do not use these

- Any 2026-dated arXiv paper whose title reads as suspiciously tailored
  to our exact claims (e.g., papers on "synthetic fraud generator
  degradation," "trust-farming in payment networks," "Shapley value
  regulatory compliance") — these could not be independently confirmed
  as real in the time available, and citing a fabricated or mismatched
  source is a worse outcome than citing nothing. If time allows before
  submission, these could be re-verified by opening each link directly.
- The "trust-farming" claim (our bounded trust-override's core
  motivation) has no strong citable source — present it as our own
  design reasoning, not as an externally-documented fraud pattern.
