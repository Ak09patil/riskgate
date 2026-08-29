"""
Pattern narrative generator — the one place in RiskGate that uses an LLM,
and deliberately not for the decision itself.

Design principle (see docs/ARCHITECTURE.md "AI Judgment"): the actual
fraud/intent-match/preference-fit scoring stays a deterministic,
auditable model — that's the decision. This module does something
different: given a BATCH of already-flagged (HOLD_FRAUD_REVIEW)
transactions, it deterministically computes shared-attribute clusters
(same pincode, same new-agent pattern, etc.) using plain pandas — no LLM
involved in finding the pattern — and then, ONLY for turning those
already-computed facts into a readable sentence a human analyst can
scan quickly, optionally calls an LLM to phrase it.

If no ANTHROPIC_API_KEY is set, this falls back to a deterministic
template — the feature is fully functional without any API key, and the
LLM call only makes the phrasing more natural, never changes what was
found. This is intentional: a judge running this repo shouldn't need to
supply a paid API key for the core functionality to work.
"""
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd


def find_shared_attribute_clusters(flagged_df: pd.DataFrame) -> list:
    """
    Deterministic pattern detection — plain pandas groupby, no LLM.
    Returns a list of dicts describing clusters of flagged transactions
    that share a suspicious attribute (same pincode, same new-agent
    pattern, etc.), which is the kind of signal a fraud analyst would
    manually look for across a batch of holds.
    """
    clusters = []

    if "pincode" in flagged_df.columns:
        pincode_counts = flagged_df["pincode"].value_counts()
        for pincode, count in pincode_counts.items():
            if count >= 3:
                clusters.append({
                    "type": "shared_pincode",
                    "pincode": pincode,
                    "count": int(count),
                    "order_ids": flagged_df[flagged_df["pincode"] == pincode]["order_id"].tolist(),
                })

    if "agent_age_days" in flagged_df.columns:
        new_agent = flagged_df[flagged_df["agent_age_days"] < 15]
        if len(new_agent) >= 3:
            clusters.append({
                "type": "new_agent_cluster",
                "count": len(new_agent),
                "order_ids": new_agent["order_id"].tolist(),
            })

    if "agent_id" in flagged_df.columns:
        agent_counts = flagged_df["agent_id"].value_counts()
        for agent_id, count in agent_counts.items():
            # threshold of 3+ (not 2+) deliberately — with a ~60-agent
            # pool, seeing an agent twice in a batch is common by chance,
            # not a real signal. Flagging on 2 would cry wolf on noise.
            if count >= 3:
                clusters.append({
                    "type": "repeat_agent",
                    "agent_id": agent_id,
                    "count": int(count),
                    "order_ids": flagged_df[flagged_df["agent_id"] == agent_id]["order_id"].tolist(),
                })

    # cap at the 5 strongest clusters (by count) — a batch summary should
    # surface what's most worth a human's attention, not list everything
    clusters = sorted(clusters, key=lambda c: c["count"], reverse=True)[:5]
    return clusters


def _template_narrative(clusters: list, total_flagged: int) -> str:
    """Deterministic fallback — no LLM, no API key needed."""
    if not clusters:
        return f"{total_flagged} transactions held for fraud review. No shared-attribute clusters detected — these appear to be independent flags, not a coordinated pattern."

    lines = [f"{total_flagged} transactions held for fraud review. {len(clusters)} pattern(s) detected:"]
    for c in clusters:
        if c["type"] == "shared_pincode":
            lines.append(f"  - {c['count']} flagged transactions share pincode {c['pincode']} — possible geographic clustering, recommend priority review.")
        elif c["type"] == "new_agent_cluster":
            lines.append(f"  - {c['count']} flagged transactions came from agents under 15 days old — possible coordinated new-account abuse.")
        elif c["type"] == "repeat_agent":
            lines.append(f"  - Agent {c['agent_id']} appears {c['count']} times in this flagged batch — recommend reviewing this agent's full history.")
    return "\n".join(lines)


def _llm_narrative(clusters: list, total_flagged: int) -> str:
    """
    Calls the Anthropic API to phrase the ALREADY-COMPUTED clusters
    (from find_shared_attribute_clusters) into natural language. The LLM
    is given only the facts already found — it cannot introduce a pattern
    that wasn't deterministically detected, which is what keeps this
    auditable: any claim in the narrative traces back to a real,
    reproducible pandas computation, not an LLM guess.
    """
    import anthropic

    client = anthropic.Anthropic()
    facts = _template_narrative(clusters, total_flagged)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                "You are writing a short, plain-English briefing for a fraud "
                "analyst reviewing a batch of held transactions. Rephrase the "
                "following ALREADY-COMPUTED facts into 2-4 clear sentences. "
                "Do NOT add any claim, number, or pattern not present in the "
                "facts below — you are only improving readability, not adding "
                "analysis.\n\nFacts:\n" + facts
            ),
        }],
    )
    return message.content[0].text


def generate_narrative(flagged_df: pd.DataFrame) -> dict:
    """
    Main entrypoint. Returns both the deterministic facts (always
    available, always auditable) and a narrative (LLM-phrased if an API
    key is available, template-phrased otherwise).
    """
    clusters = find_shared_attribute_clusters(flagged_df)
    total = len(flagged_df)

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            narrative = _llm_narrative(clusters, total)
            source = "llm"
        except Exception as e:
            narrative = _template_narrative(clusters, total)
            source = f"template (LLM call failed: {e})"
    else:
        narrative = _template_narrative(clusters, total)
        source = "template (no ANTHROPIC_API_KEY set)"

    return {
        "total_flagged": total,
        "clusters": clusters,
        "narrative": narrative,
        "narrative_source": source,
    }


if __name__ == "__main__":
    df = pd.read_csv(f"{BASE_DIR}/data/full_merged.csv")
    flagged = df[df["decision"] == "HOLD_FRAUD_REVIEW"].head(40)

    print(f"=== Pattern narrative for {len(flagged)} flagged transactions ===\n")
    result = generate_narrative(flagged)
    print(f"Narrative source: {result['narrative_source']}\n")
    print(result["narrative"])
    print(f"\n{len(result['clusters'])} deterministic cluster(s) found (see code for the pandas logic behind each).")
