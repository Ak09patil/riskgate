"""
Fraud-spike detector — a third, genuinely different problem shape from
everything else in RiskGate. Fraud-risk and intent-match are per-
transaction classification. The abuse-ring sentinel is relational/graph
detection. This is TIME-SERIES ANOMALY DETECTION: does the aggregate
fraud RATE over a period of time look statistically abnormal, even if
no single transaction in that window looks individually alarming
enough to trigger a hold on its own?

WHY THIS IS A REAL, DIFFERENT BLIND SPOT (see docs/ARCHITECTURE.md):
Imagine 40 transactions arrive in a short window from a category that
normally sees a handful a day, each individually scoring "moderate"
risk — not high enough to hold on its own. No single transaction looks
bad enough to block. The RATE itself is the anomaly, and nothing in the
per-transaction or per-cluster architecture is built to see that.

METHOD: bucket transactions into fixed-width time windows, compute the
observed fraud rate per bucket, and flag a bucket as anomalous if its
rate is far from the TYPICAL bucket's rate — measured with median and
MAD (median absolute deviation), not mean/std. This is a deliberate
choice: a handful of genuinely spiking buckets would drag a mean/std
baseline upward too, partially hiding themselves. Median/MAD is the
standard robust-statistics choice for exactly this reason — the same
"pick the technique for a stated reason, not because it's fancier"
discipline used throughout this project.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

BUCKET_MINUTES = 120
MIN_BUCKET_COUNT = 5  # buckets with fewer transactions are too noisy to judge
Z_THRESHOLD = 3.0  # how many MADs above the median counts as "anomalous"


def detect_spikes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Buckets transactions into fixed time windows and returns a
    per-bucket DataFrame with observed fraud rate, count, and whether
    each bucket was flagged as an anomalous spike.
    """
    df = df.copy()
    df["_ts"] = pd.to_datetime(df["timestamp"])
    df["_bucket"] = df["_ts"].dt.floor(f"{BUCKET_MINUTES}min")

    bucket_stats = df.groupby("_bucket").agg(
        count=("is_fraud", "size"),
        fraud_rate=("is_fraud", "mean"),
        true_spike=("true_spike_window", "max"),  # bucket overlaps a true spike window if ANY member does
    ).reset_index()

    # only judge buckets with enough data to mean something
    judgeable = bucket_stats[bucket_stats["count"] >= MIN_BUCKET_COUNT]
    median_rate = judgeable["fraud_rate"].median()
    mad = (judgeable["fraud_rate"] - median_rate).abs().median()
    # avoid division by zero if MAD is 0 (all typical buckets identical) —
    # fall back to a small floor so a single differing bucket doesn't
    # get an infinite z-score
    mad_floor = max(mad, 0.02)

    bucket_stats["z_score"] = (bucket_stats["fraud_rate"] - median_rate) / mad_floor
    bucket_stats["detected_spike"] = (
        (bucket_stats["count"] >= MIN_BUCKET_COUNT) & (bucket_stats["z_score"] >= Z_THRESHOLD)
    )

    return bucket_stats


def validate_against_ground_truth(bucket_stats: pd.DataFrame) -> dict:
    """
    Honest precision/recall at the BUCKET level against the injected
    true_spike_window ground truth.
    """
    detected = bucket_stats["detected_spike"]
    truth = bucket_stats["true_spike"].astype(bool)

    tp = int((detected & truth).sum())
    fp = int((detected & ~truth).sum())
    fn = int((~detected & truth).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "true_positive_buckets": tp,
        "false_positive_buckets": fp,
        "false_negative_buckets": fn,
        "total_buckets": len(bucket_stats),
        "true_spike_buckets": int(truth.sum()),
    }


if __name__ == "__main__":
    df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
    bucket_stats = detect_spikes(df)

    print("=== Fraud-spike detector ===")
    print(f"{len(bucket_stats)} time buckets ({BUCKET_MINUTES}-minute width), "
          f"{bucket_stats['detected_spike'].sum()} flagged as anomalous\n")

    metrics = validate_against_ground_truth(bucket_stats)
    print("=== Validation against injected ground truth (true_spike_window) ===")
    print(f"Precision: {metrics['precision']}  (of flagged buckets, this fraction genuinely overlapped an injected spike)")
    print(f"Recall:    {metrics['recall']}  (of buckets that genuinely overlapped a spike, this fraction was caught)")
    print(f"True positive buckets: {metrics['true_positive_buckets']}, "
          f"False positive buckets: {metrics['false_positive_buckets']}, "
          f"False negative buckets: {metrics['false_negative_buckets']}")
    print("\nTop 10 buckets by z-score:")
    print(bucket_stats.sort_values("z_score", ascending=False).head(10)[
        ["_bucket", "count", "fraud_rate", "z_score", "detected_spike", "true_spike"]
    ].to_string(index=False))
