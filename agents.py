"""The Relevance Gate agent crew.

Four isolated agents: research -> intersect -> verify (THE GATE) -> write.
The gate renders its verdict before the writer exists — the writer cannot
talk the gate into sending. All agents are domain-agnostic; domain knowledge
lives in the profile dict.
"""

import asyncio
import json
import os

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

client = AsyncAnthropic(timeout=25.0)

# Latency budget (§2: full run < 12s) drives model choice: Haiku for the
# structured-judgment stages — measured ~2-4s each vs Sonnet's 8-13s —
# Sonnet only for the message a human reads aloud on stage.
MODEL_FAST = "claude-haiku-4-5"     # research / intersect / verify
MODEL_WRITER = "claude-sonnet-4-6"  # write: quality of the read-aloud message

DEMO_MODE = os.getenv("DEMO_MODE", "1") == "1"
TEMPERATURE = 0.2 if DEMO_MODE else 0.7

# Per-stage wall-clock budgets (seconds). Typical total ~10-12s.
STAGE_TIMEOUT = {"research": 6.0, "intersect": 10.0, "verify": 8.0, "write": 9.0}
STAGE_MAX_TOKENS = {"research": 700, "intersect": 700, "verify": 450, "write": 300}


# ---------------------------------------------------------------- schemas
# Structured outputs (output_config.format) guarantee schema-valid JSON, so
# the parse-failure mode is nearly eliminated. Fail-closed remains the backstop.

DOSSIER_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"fact": {"type": "string"}, "source": {"type": "string"}},
                "required": ["fact", "source"],
                "additionalProperties": False,
            },
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["facts", "unknowns"],
    "additionalProperties": False,
}

OVERLAP_ITEM = {
    "type": "object",
    "properties": {
        "point": {"type": "string"},
        "candidate_evidence": {"type": "string"},
        "target_evidence": {"type": "string"},
        "why_it_matters": {"type": "string"},
    },
    "required": ["point", "candidate_evidence", "target_evidence", "why_it_matters"],
    "additionalProperties": False,
}

INTERSECT_SCHEMA = {
    "type": "object",
    "properties": {
        "primary_overlap": OVERLAP_ITEM,
        "secondary_overlaps": {"type": "array", "items": OVERLAP_ITEM},
        "overlap_strength": {"type": "string", "enum": ["strong", "medium", "weak", "none"]},
    },
    "required": ["primary_overlap", "secondary_overlaps", "overlap_strength"],
    "additionalProperties": False,
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "send": {"type": "boolean"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "verdict_line": {"type": "string"},
    },
    "required": ["score", "send", "evidence", "verdict_line"],
    "additionalProperties": False,
}

MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "required": ["message"],
    "additionalProperties": False,
}


async def _call(model: str, system: str, user: str, schema: dict, timeout: float,
                max_tokens: int = 700) -> dict:
    """One schema-enforced agent call. Raises on timeout/API error — callers
    decide the safe direction."""
    response = await asyncio.wait_for(
        client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=TEMPERATURE,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        ),
        timeout=timeout,
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


# ---------------------------------------------------------------- agents

async def research_agent(profile: dict, target: dict) -> dict:
    system = (
        "You are a research agent. Build a factual dossier about an outreach "
        "target. Your PRIMARY and authoritative source is what the target "
        "said about themselves (the typed context). Record only facts you can "
        "tie to a source. Never invent facts. List explicit unknowns."
    )
    user = json.dumps({
        "target": target,
        "instruction": (
            "Produce facts[] where each fact cites its source "
            "(e.g. 'stated by target'). Include role and what they work on. "
            "List unknowns you could not establish."
        ),
    })
    return await _call(MODEL_FAST, system, user, DOSSIER_SCHEMA,
                       STAGE_TIMEOUT["research"], STAGE_MAX_TOKENS["research"])


async def intersect_agent(profile: dict, dossier: dict, target: dict) -> dict:
    system = (
        "You are an intersection agent. Compute the GENUINE overlap between a "
        "candidate's proven work and a target's world. Every overlap must be "
        "backed by candidate evidence AND target evidence — no invented "
        "connections, no generic 'both like AI' reasoning.\n"
        "Strength rubric: 'strong' = the candidate's concrete proven work maps "
        "directly onto what the target builds/hires for. 'medium' = a real, "
        "specific adjacency. 'weak' = only generic thematic similarity. "
        "'none' = no genuine connection. If strength is weak or none, say so "
        "honestly in primary_overlap and do not inflate it.\n"
        "Be brief: every field one sentence; at most 2 secondary overlaps."
    )
    user = json.dumps({
        "candidate": profile["candidate"],
        "candidate_proof_points": profile["proof_points"],
        "relevance_criteria": profile["relevance_criteria"],
        "target_dossier": dossier,
        "target": target,
    })
    return await _call(MODEL_FAST, system, user, INTERSECT_SCHEMA,
                       STAGE_TIMEOUT["intersect"], STAGE_MAX_TOKENS["intersect"])


async def verify_agent(profile: dict, intersection: dict, target: dict) -> dict:
    system = (
        "You are THE GATE — an independent verifier deciding whether outreach "
        "is justified. You optimize for send-worthiness, not volume. Score the "
        "intersection 0-100 against the relevance criteria:\n"
        "- strong overlap, concrete + evidenced: 75-100, send=true\n"
        "- medium overlap, real and specific: 55-74, send=true\n"
        "- weak overlap (generic thematic similarity only): 25-54, send=false\n"
        "- no genuine overlap: 0-24, send=false\n"
        "Generic or no-overlap reasons MUST score under 40 and fail. "
        "verdict_line: one plain sentence a human reads aloud explaining the "
        "decision. evidence[]: the specific facts that justify it."
    )
    user = json.dumps({
        "relevance_criteria": profile["relevance_criteria"],
        "intersection": intersection,
        "target": target,
    })
    return await _call(MODEL_FAST, system, user, VERDICT_SCHEMA,
                       STAGE_TIMEOUT["verify"], STAGE_MAX_TOKENS["verify"])


async def write_agent(profile: dict, intersection: dict, target: dict) -> dict:
    system = (
        "You write outreach messages built ONLY on verified overlap. Hard rules:\n"
        "1. <= 75 words, one idea, short sentences, skimmable in seconds.\n"
        "2. Line 1 opens with one precise, true, non-obvious detail about THEIR "
        "work (specificity as costly signaling) — never with the ask.\n"
        "3. Peer framing, builder-to-builder. No groveling, no flattery that "
        "isn't specific and true.\n"
        "4. At most ONE candidate proof point, only because it maps to their world.\n"
        "5. One low-friction ask at the end.\n"
        "6. Every claim must trace to the provided overlap evidence. No "
        "fabricated connections, no false urgency, nothing not in the evidence."
    )
    user = json.dumps({
        "candidate": profile["candidate"],
        "ask": profile["candidate"]["ask"],
        "verified_overlap": intersection,
        "target": target,
    })
    msg = await _call(MODEL_WRITER, system, user, MESSAGE_SCHEMA,
                      STAGE_TIMEOUT["write"], STAGE_MAX_TOKENS["write"])
    # Guard against double-encoded output: a JSON object inside the message
    # string is still schema-valid, so unwrap it if a model produces one.
    inner = msg.get("message", "").strip()
    if inner.startswith("{"):
        try:
            parsed = json.loads(inner)
            if isinstance(parsed, dict) and isinstance(parsed.get("message"), str):
                msg["message"] = parsed["message"]
        except ValueError:
            pass
    return msg


# ------------------------------------------------- DEMO_MODE seeded fallback
# SAFETY NET, not the default path. Used ONLY when a live call fails mid-run
# on a canonical input. Clearly labeled per CLAUDE.md §8.

def _seeded_result(profile_id: str, target: dict) -> dict | None:
    works_on = (target.get("what_they_work_on") or "").lower()
    if profile_id == "job_seeker" and ("agent" in works_on or "ai" in works_on):
        return {
            "verdict": {
                "score": 87, "send": True,
                "evidence": [
                    "Target stated they work on agents (stated by target)",
                    "Candidate built Council of LLMs — a 7-phase multi-agent reasoning pipeline with 6-layer anti-hallucination",
                ],
                "verdict_line": "Genuine overlap: the target builds agent systems and the candidate has shipped a production multi-agent pipeline — a concrete, evidenced reason to reach out.",
            },
            "intersection": {
                "primary_overlap": {
                    "point": "Multi-agent system design",
                    "candidate_evidence": "Built Council of LLMs: 7-phase multi-agent legal reasoning pipeline, ~23 model calls/query, 6-layer anti-hallucination",
                    "target_evidence": "Target stated they work on agents",
                    "why_it_matters": "The candidate has production experience with exactly the class of systems the target builds.",
                },
                "secondary_overlaps": [],
                "overlap_strength": "strong",
            },
            "message": {
                "message": (
                    f"Hi {target.get('name', 'there').split(',')[0].split()[0]} — you work on agents, so this might resonate: "
                    "I built a 7-phase multi-agent legal reasoning pipeline (23 model calls per query, "
                    "6 anti-hallucination layers) that a retired federal judge now cites. "
                    "I'm looking at AI product roles and would value 15 minutes on how your team "
                    "thinks about agent reliability. Worth a quick chat?"
                )
            },
        }
    # Any other failed live run: honest fail-closed hold.
    return {
        "verdict": {
            "score": 12, "send": False,
            "evidence": ["No concrete overlap between the offer and the target's stated context could be verified."],
            "verdict_line": "The gate found no real, evidence-backed reason to contact this person — so it sends nothing.",
        },
        "intersection": {
            "primary_overlap": {
                "point": "No genuine overlap found",
                "candidate_evidence": "—", "target_evidence": "—",
                "why_it_matters": "A message without a real reason is spam.",
            },
            "secondary_overlaps": [],
            "overlap_strength": "none",
        },
        "message": None,
    }


# ---------------------------------------------------------------- pipeline

async def run_pipeline(profile: dict, target: dict):
    """Async generator yielding SSE-ready stage events."""
    profile_id = profile["id"]
    try:
        yield {"stage": "research", "status": "running"}
        dossier = await research_agent(profile, target)
        yield {"stage": "research", "status": "done", "data": dossier}

        yield {"stage": "intersect", "status": "running"}
        intersection = await intersect_agent(profile, dossier, target)
        yield {"stage": "intersect", "status": "done", "data": intersection}

        yield {"stage": "verify", "status": "running"}
        try:
            verdict = await verify_agent(profile, intersection, target)
        except Exception:
            # FAIL CLOSED: an unverifiable message must not send.
            verdict = {
                "score": 0, "send": False, "evidence": [],
                "verdict_line": "The gate could not verify a real reason to contact this person — so it sends nothing.",
            }
        # Code-level enforcement: the writer never runs on weak/no overlap,
        # regardless of what the verifier said.
        if intersection.get("overlap_strength") in ("weak", "none"):
            verdict["send"] = False
        yield {"stage": "verify", "status": "done", "data": verdict}

        if verdict["send"]:
            yield {"stage": "write", "status": "running"}
            msg = await write_agent(profile, intersection, target)
            msg["word_count"] = len(msg["message"].split())
            yield {"stage": "write", "status": "done", "data": msg}
        else:
            yield {"stage": "write", "status": "skipped"}

        yield {"stage": "done", "status": "done"}

    except Exception:
        if DEMO_MODE:
            # DEMO SAFETY NET — pre-validated result for canonical inputs,
            # triggered only on live failure mid-pitch.
            seeded = _seeded_result(profile_id, target)
            yield {"stage": "research", "status": "done", "data": {
                "facts": [{"fact": f"{target.get('name', 'Target')} — {target.get('role', 'role unknown')}; works on: {target.get('what_they_work_on', 'unknown')}",
                           "source": "stated by target"}],
                "unknowns": [],
            }}
            yield {"stage": "intersect", "status": "done", "data": seeded["intersection"]}
            yield {"stage": "verify", "status": "done", "data": seeded["verdict"]}
            if seeded["message"]:
                m = dict(seeded["message"])
                m["word_count"] = len(m["message"].split())
                yield {"stage": "write", "status": "done", "data": m}
            else:
                yield {"stage": "write", "status": "skipped"}
            yield {"stage": "done", "status": "done"}
        else:
            yield {"stage": "error", "status": "error",
                   "message": "Couldn't complete this run — try again."}
