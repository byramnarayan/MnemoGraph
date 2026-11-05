from __future__ import annotations

NARRATIVE_DEEPDIVE_SYSTEM_PROMPT = """
You are MnemoGraph Institutional Intelligence Engine.
Synthesize a comprehensive, executive-level operational narrative deep-dive for an unmitigated institutional decision.

STRICT INSTRUCTIONS:
1. DO NOT output cold technical database identifiers (e.g. avoid 'sys:123', 'dec:abc', raw URLs, or database column names). Refer to real operational entities and people by their professional names (e.g., 'Bandra Kurla Telecom Tower', 'Lead Infrastructure Architect Arjun Nair').
2. Write a rich, fluent, continuous operational story divided into exactly four labeled sections:
   1. EXECUTIVE SCENARIO & FAILURE MODE
   2. CHRONOLOGICAL TIMELINE DESCRIPTION
   3. INTERCONNECTED GRAPH & INFRASTRUCTURE CONTEXT
   4. HISTORICAL PRECEDENTS & LESSONS LEARNED
3. Include inline citations [1], [2], [3] directly referencing the provided facts.
4. Highlight what tasks were implemented vs left incomplete, what telemetry/jitter anomalies are emerging, and why downstream systems represent single points of failure.
"""

def format_deepdive_context(
    decision_title: str,
    decision_maker: str,
    rationale: str,
    tasks_str: str,
    target_scope: str,
    neighbors_str: str,
    lanobert_score: float,
    lanobert_trend: str,
    qdrant_lessons: str,
) -> str:
    return (
        f"Operational Decision: '{decision_title}'\n"
        f"Decision Maker: {decision_maker}\n"
        f"Authorized Rationale: {rationale}\n"
        f"Associated Tasks & Implementation Status: {tasks_str}\n"
        f"Primary Affected Facility/System: {target_scope}\n"
        f"Connected Downstream Infrastructure: {neighbors_str}\n"
        f"Real-Time Telemetry Anomaly (LAnoBERT error_mean): {lanobert_score:.2f} (Trend: {lanobert_trend})\n"
        f"Documented Post-Mortems & Precedents: {qdrant_lessons}\n"
    )

