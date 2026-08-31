"""
Abuse-ring sentinel — a genuinely different problem shape from
fraud-risk and intent-match. Those are per-transaction classification.
This is relational/graph detection: is transaction A linked to
transaction B through shared suspicious attributes and tight timing,
forming a cluster that looks like coordinated abuse rather than
independent honest customers?

WHY THIS, SPECIFICALLY (see docs/ARCHITECTURE.md for the full reasoning):
We don't have device fingerprints or shared payment instruments in this
data — the honest, available signal for coordination is: multiple
FRESH agents (<10 days old — a ring is usually farmed with newly
created accounts, not established ones), sharing the SAME pincode,
transacting within a TIGHT real time window. Any one of these alone
means little. Together, they're the actual signature of coordinated
abuse, not coincidence — and no single-transaction model can see this,
because the signal only exists in the relationship BETWEEN transactions.

METHOD: union-find (connected components) over an edge rule — two
transactions are linked if same pincode, both agents <10 days old, and
within FRESH_AGENT_WINDOW_MINUTES of each other. Clusters of size >= 3
are flagged as a detected ring. This is deliberately simple and
auditable (same "why simple, not flashy" principle used for the
scoring models) — not a black-box graph embedding.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

FRESH_AGENT_AGE_DAYS = 10
LINK_WINDOW_MINUTES = 90
MIN_RING_SIZE = 3


class UnionFind:
    """Plain, auditable union-find — not imported from a graph library,
    so the whole detection logic is inspectable in one file, consistent
    with the project's preference for simple/explainable over black-box."""
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def detect_rings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the input df with an added 'detected_ring_id' column
    (-1 if not part of any detected ring, else a cluster id).
    """
    df = df.copy()
    df["_ts"] = pd.to_datetime(df["timestamp"])
    df["detected_ring_id"] = -1

    fresh = df[df["agent_age_days"] < FRESH_AGENT_AGE_DAYS].copy()
    if len(fresh) < MIN_RING_SIZE:
        return df

    fresh = fresh.reset_index()  # keep original df index as a column
    uf = UnionFind(len(fresh))

    # group by pincode — links can only form within the same pincode —
    # then within each pincode group, sort by time and union any pair
    # within the window. This is O(n log n) per pincode group instead of
    # O(n^2) over the whole fresh set.
    for pincode, group in fresh.groupby("pincode"):
        group = group.sort_values("_ts")
        rows = group[["_ts"]].reset_index()  # 'index' col = position in `fresh`
        n = len(rows)
        for a in range(n):
            for b in range(a + 1, n):
                delta = (rows.iloc[b]["_ts"] - rows.iloc[a]["_ts"]).total_seconds() / 60
                if delta > LINK_WINDOW_MINUTES:
                    break  # sorted by time — no later b can be closer
                uf.union(rows.iloc[a]["index"], rows.iloc[b]["index"])

    # collect connected components, keep only size >= MIN_RING_SIZE
    roots = {}
    for i in range(len(fresh)):
        r = uf.find(i)
        roots.setdefault(r, []).append(i)

    ring_id = 0
    for members in roots.values():
        if len(members) >= MIN_RING_SIZE:
            for m in members:
                original_idx = fresh.loc[m, "index"]
                df.loc[original_idx, "detected_ring_id"] = ring_id
            ring_id += 1

    return df.drop(columns=["_ts"])


def validate_against_ground_truth(df: pd.DataFrame) -> dict:
    """
    Honest precision/recall against the injected true_ring_id ground
    truth — the same rigor standard as the fraud/intent-match models,
    not just 'does this look plausible.'
    """
    detected_positive = df["detected_ring_id"] >= 0
    true_positive_label = df["true_ring_id"] >= 0

    tp = int((detected_positive & true_positive_label).sum())
    fp = int((detected_positive & ~true_positive_label).sum())
    fn = int((~detected_positive & true_positive_label).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # ring-level recovery: for each TRUE ring, was a majority of its
    # members captured together in the SAME detected cluster?
    true_rings = df[df["true_ring_id"] >= 0]["true_ring_id"].unique()
    recovered = 0
    for tid in true_rings:
        members = df[df["true_ring_id"] == tid]
        detected_ids = members["detected_ring_id"]
        detected_ids = detected_ids[detected_ids >= 0]
        if len(detected_ids) == 0:
            continue
        most_common_cluster = detected_ids.mode()
        if len(most_common_cluster) == 0:
            continue
        matched = (detected_ids == most_common_cluster.iloc[0]).sum()
        if matched >= len(members) / 2:  # majority of the true ring landed in one cluster
            recovered += 1

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_rings_total": len(true_rings),
        "true_rings_recovered": recovered,
        "ring_recovery_rate": round(recovered / len(true_rings), 3) if len(true_rings) else 0.0,
    }


if __name__ == "__main__":
    df = pd.read_csv(f"{BASE_DIR}/data/transactions.csv")
    result_df = detect_rings(df)

    n_detected_rings = result_df[result_df["detected_ring_id"] >= 0]["detected_ring_id"].nunique()
    n_detected_txns = (result_df["detected_ring_id"] >= 0).sum()
    print("=== Abuse-ring sentinel ===")
    print(f"Detected {n_detected_rings} ring(s), {n_detected_txns} transactions total\n")

    metrics = validate_against_ground_truth(result_df)
    print("=== Validation against injected ground truth (true_ring_id) ===")
    print(f"Precision: {metrics['precision']}  (of flagged transactions, this fraction were truly part of an injected ring)")
    print(f"Recall:    {metrics['recall']}  (of truly-ringed transactions, this fraction was caught)")
    print(f"True positives: {metrics['true_positives']}, False positives: {metrics['false_positives']}, False negatives: {metrics['false_negatives']}")
    print(f"\nRing-level recovery: {metrics['true_rings_recovered']}/{metrics['true_rings_total']} injected rings "
          f"had a majority of their members captured together in one detected cluster "
          f"({metrics['ring_recovery_rate']*100:.1f}%)")
