"""Offer profiles — the domain switch. ALL domain knowledge lives here.
The agents are 100% domain-agnostic; swapping the dropdown changes behavior
with zero code change."""

PROFILES = {
    "job_seeker": {
        "id": "job_seeker",
        "label": "AI Product Roles (Job Seeker)",
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
    "roofing": {
        "id": "roofing",
        "label": "Roofing Services (Local Contractor)",
        "candidate": {
            "name": "Summit Roofing Co.",
            "identity": "a licensed local roofing contractor with 200+ completed storm-damage restorations",
            "goal": "book free roof inspections for homeowners with genuine roof issues",
            "ask": "a free 20-minute roof inspection",
        },
        "proof_points": [
            {
                "point": "200+ insurance-approved storm-damage restorations",
                "evidence": "5-star average across 80+ verified local reviews",
            },
            {
                "point": "Certified for hail and wind damage assessment",
                "evidence": "HAAG-certified inspectors on staff",
            },
        ],
        "relevance_criteria": (
            "A real reason exists ONLY if the target shows a concrete roof-related "
            "need: visible damage, recent severe weather in their area, an aging "
            "roof, an active insurance claim, or they manage properties. Owning a "
            "home is NOT enough. Mowing a lawn is NOT a roofing signal."
        ),
    },
    "ceramic_coating": {
        "id": "ceramic_coating",
        "label": "Ceramic Coating (Auto Detailing)",
        "candidate": {
            "name": "Mirror Finish Detailing",
            "identity": "a paint-correction and ceramic-coating studio",
            "goal": "book ceramic coating consultations for owners of new or high-value vehicles",
            "ask": "a quick quote on protecting their specific vehicle",
        },
        "proof_points": [
            {
                "point": "300+ ceramic coating applications on luxury and exotic vehicles",
                "evidence": "certified Gtechniq and Ceramic Pro installer",
            },
        ],
        "relevance_criteria": (
            "A real reason exists ONLY if the target recently acquired a new or "
            "high-value vehicle, shows pride in their car's appearance, or asked "
            "about paint protection. Merely owning any car is NOT enough."
        ),
    },
}
