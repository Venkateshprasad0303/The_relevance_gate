"""Seeker profiles. ALL personal context lives here — the agents are
profile-agnostic, so a custom profile built from a pasted résumé runs
through the identical pipeline with zero code change."""

PROFILES = {
    "job_seeker": {
        "id": "job_seeker",
        "label": "Venkatesh — AI Product Roles",
        "candidate": {
            "name": "Venkatesh Prasad Ravichandran",
            "identity": "a PM who can build and an engineer who thinks in products",
            "goal": "PM or AI Product role at a serious AI company",
            "ask": "a brief reply or a 15-minute chat",
        },
        "proof_points": [
            {
                "point": "Council of LLMs — 7-phase multi-agent legal reasoning pipeline",
                "evidence": "~23 model calls/query, 6-layer anti-hallucination, ~90% cost reduction via prompt caching; cited by a retired federal judge",
            },
            {
                "point": "Fred the Heretic — production RAG system",
                "evidence": "~80% stylistic alignment, expert-validated",
            },
            {
                "point": "Coalition Restoration Ops Platform — AI automation",
                "evidence": "70% manual email-triage reduction, 40% admin-overhead cut, zero post-launch defects",
            },
        ],
        "relevance_criteria": (
            "A real reason exists ONLY if the target builds, hires for, or "
            "influences AI product, agent, or RAG work that the candidate's "
            "proof points map onto concretely. Shared generic interest in 'AI' "
            "is NOT enough. The overlap must be concrete and specific."
        ),
    },
}
