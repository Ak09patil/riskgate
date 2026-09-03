# References

## Foundational

**Chen, T., & Guestrin, C. (2016).** XGBoost: A Scalable Tree Boosting System. *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '16).*
https://doi.org/10.1145/2939672.2939785
*Basis for the production fraud-risk model architecture.*

**Lundberg, S. M., & Lee, S.-I. (2017).** A Unified Approach to Interpreting Model Predictions. *Advances in Neural Information Processing Systems 30 (NeurIPS 2017).*
https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html
*Basis for the SHAP feature-importance analysis in train_fraud_model.py.*

**Niculescu-Mizil, A., & Caruana, R. (2005).** Predicting Good Probabilities with Supervised Learning. *Proceedings of the 22nd International Conference on Machine Learning (ICML 2005).*
https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf
*Basis for the Platt-scaling calibration approach.*

**Zadrozny, B., & Elkan, C. (2002).** Transforming Classifier Scores into Accurate Multiclass Probability Estimates. *Proceedings of the 8th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD 2002).*
https://doi.org/10.1145/775047.775111
*Alternative calibration method (isotonic regression), referenced for comparison.*

**Morris, C. N. (1983).** Parametric Empirical Bayes Inference: Theory and Applications. *Journal of the American Statistical Association*, 78(381), 47-55.
https://doi.org/10.1080/01621459.1983.10500471
*Basis for the empirical-Bayes shrinkage technique used in compute_shrunk_pincode_rates() and compute_shrunk_pincode_ring_rates().*

**Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., He, Q., & Liu, T.-Y. (2017).** LightGBM: A Highly Efficient Gradient Boosting Decision Tree. *Advances in Neural Information Processing Systems 30 (NeurIPS 2017).*
https://proceedings.neurips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html
*Background reference for the model comparison in full_model_comparison.py and held_out_validation.py.*

## Industry practice

**Stripe.** How a Fraud Score Works: A Guide for Businesses.
https://stripe.com/resources/more/fraud-scores-explained

**MaxMind.** Set Thresholds for Risk Scores (minFraud).
https://support.maxmind.com/knowledge-base/articles/set-thresholds-for-risk-scores-minfraud

Both referenced for the multi-tier threshold pattern used in RiskGate's two-tier gating design.

**Razorpay.** Cash on Delivery in India: Benefits, Risks & RTO Tips.
https://razorpay.com/blog/cash-on-delivery/
Referenced for COD-related RTO risk context in India; the specific figure cited should be re-verified against the current page before direct quotation.
