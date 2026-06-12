# CLAUDE.md — Master Context & Build Brief: The Relevance Gate

> You are building a hackathon-winning demo solo, under a hard deadline. Read this
> whole file before writing code. Build in the **sequenced increments** in §7, and
> **stop at each VERIFY gate** before moving on. The single most important property
> of this project is: **the live demo must not break on stage.** Reliability beats
> features. When in doubt, choose the simpler, more deterministic path.

---

## 1. North Star — what we're building and why

**The product:** an outreach agent crew that **refuses to send unless it finds a
real, evidence-backed reason** to contact someone. It researches a target, finds
the genuine *intersection* between the sender's offer and the target's world, and
either (a) writes a short, psychologically-grounded message built entirely on that
intersection, or (b) declines and says why. **Found many, contact few. All true.**

**The one idea that makes it defensible:** every other outreach tool optimizes for
*volume* and fakes personalization. We optimize for *send-worthiness*. Our headline
feature is the message we **won't** send.

**Validated market truth (use in pitch):** generic cold outreach replies at ~3.43%;
signal-based, evidence-grounded outreach replies at 15–25% (a ~5x lift). Recipients
skim and delete in ~0.1 seconds, discarding ~90% on sight. We are the only system
that won't generate the spam-engagement pattern because it won't send without a
verified reason.

**The wedge we demo:** a job seeker (the builder) reaching out to people who could
hire or refer. **The company we pitch:** a "relevance layer" any outreach tool can
plug into. Build the wedge; speak the vision.

---

## 2. THE LIVE DEMO — this drives every requirement below

This is exactly how it will be pitched. Engineer everything to make this flawless.

### The choreography
1. Presenter turns to a judge: *"What's your name, and what do you work on?"*
2. Judge says e.g. *"I'm Gagan, MTS at Anthropic, I work on agents."*
3. Presenter types that into the **Target** + **What they work on** fields and hits run.
4. On screen, live: the crew researches → the gate finds the **intersection** with the
   candidate's real background → scores it → shows the **evidence/overlap** → writes a
   short message grounded only in that overlap.
5. Presenter reads the line that proves it: the strongest genuine connection point.
6. Then: presenter switches the **context** dropdown to *Roofing*, types a clearly
   unrelated target, runs it → **the gate HOLDS** → "it found no real reason, so it
   sends nothing. No other agent in this room declines to act." ← the moment.
7. Close: "Same engine, any niche. Found many, contacted few, all of them true."

### Non-negotiable demo rules (encode these as constraints)
- **The grounding input is what the judge SAYS, not what we scrape.** A free-text
  "what they work on / recent work" field is the primary signal. Live web/Composio
  enrichment is **additive only** and must never block or slow the critical path.
- **Never block a judge during the match segment.** The judge↔candidate overlap (both
  in AI/agents) must reliably PASS with a strong score. Tune the gate so a genuine
  overlap clears. The REFUSAL is demonstrated separately with a **deliberately
  irrelevant** target (e.g. a roofing lead, or someone with zero overlap) — never a judge.
- **Hard latency budget: a full run returns in < 12 seconds.** If enrichment is slow,
  time it out at 4s and proceed with what we have. A fast honest result beats a rich
  slow one.
- **No raw errors ever reach the screen.** Every failure degrades to a friendly state.
- **Determinism for the demo:** support a `DEMO_MODE` that lowers temperature and can
  fall back to a cached/seeded result if a live call fails mid-pitch (see §8).

---

## 3. Pain points → product requirements (each feature must trace to a real pain)

| Validated pain (in users' words) | Requirement it forces |
|---|---|
| "Personalization" is token-insertion; reads as mass mail | Writer may only use claims tied to verified evidence — no generic flattery |
| Recipients skim & delete in 0.1s; 90% discarded | Message ≤ 75 words, one idea, skimmable, specific hook in line 1 |
| Volume death-loop torches sender reputation | The gate can return send=false; we optimize for fewer, justified sends |
| True personalization is too time-consuming | Research + intersection-finding is automated end to end |
| "Just network" is vague; can't tell who's hiring | Discovery works from **signals** (what they work on / are hiring for), not names |
| Trust erosion — "they don't owe you their time" | Every claim sourced; value-first, low-friction ask; peer (not supplicant) framing |

If a feature doesn't trace to a row here, don't build it.

---

## 4. Architecture (extend the EXISTING repo, don't restart)

The repo already exists with this scaffold — build on it:

```
agents.py     # discover_agent, research_agent, verify_agent (THE GATE), write_agent, run_pipeline
profiles.py   # offer profiles = the domain switch (job_seeker / roofing / ceramic_coating)
main.py       # FastAPI: /api/profiles, /api/discover, /api/generate
static/index.html  # two-step UI: search → candidates → gate
render.yaml, requirements.txt, README.md
```

### The agent crew (4 agents, Claude is the brain of each — Anthropic)
```
INPUTS:  candidate/offer profile (config)  +  target {name, role, what_they_work_on}
   │
   ▼
① RESEARCH   build a SOURCED dossier {fact, source}[] + explicit unknowns.
             Primary source = what the target SAID (the typed context).
             Optional enrichment = web/Composio (additive, ≤4s, never blocks).
   ▼
② INTERSECT  (NEW — the heart of the "matching" pitch) compute the genuine overlap
             between the candidate's proven work and the target's world. Output the
             single STRONGEST connection point + supporting overlaps, each sourced.
   ▼
③ VERIFY ← THE GATE. score 0–100 + send bool + evidence[] + verdict_line.
             Strict: generic/no-overlap reasons score < 40 and FAIL.
             Fails CLOSED on parse error (send=false) — safe direction.
   ▼
④ WRITE (only if send=true)  ≤75-word message built ONLY on the verified overlap,
             following the Relevance Psychology spec (§5).

CROSS-CUTTING:  Langfuse traces every agent call. ClickHouse logs every verdict.
HOSTING:        Render. FLAGSHIP PRIZE narrative: Guild (an agent that refuses to act).
```

**Why 4 separate agents, not one prompt (say this to judges):** retrieval, judgment,
and generation are isolated so the **writer cannot talk the gate into sending.** The
gate renders its verdict before the writer exists. That independence is the
anti-hallucination property — the same principle as a verifier that can't be co-opted
by the generator.

### The Intersection agent (NEW — implement carefully, it's the pitch centerpiece)
- Input: candidate profile proof-points + target dossier.
- Output JSON: `{ "primary_overlap": {"point": str, "candidate_evidence": str,
  "target_evidence": str, "why_it_matters": str}, "secondary_overlaps": [...],
  "overlap_strength": "strong|medium|weak|none" }`.
- This is what makes the live demo land: when a judge says "I work on agents" and the
  candidate built multi-agent systems, `primary_overlap` surfaces that exact match,
  and the writer builds the message around it. The gate scores largely off
  `overlap_strength`.

---

## 5. Relevance Psychology spec (the WRITE agent's rules — ethical, not manipulative)

The message must use how humans actually decide to reply — grounded in the pain
research — **without any dark patterns.** Truth is enforced upstream by the gate, so
psychology here = making a *true, relevant* message land. Encode these as hard rules
in the write agent's system prompt:

1. **Specificity as costly signaling.** Open with one precise, true, non-obvious
   detail about their work that proves real attention. This is the single biggest
   driver of a reply — it signals effort no mass-sender spends.
2. **Reciprocity / value-first.** Lead with a genuine observation, insight, or point
   of connection — never with the ask. Give before you take.
3. **Peer framing, not supplicant.** Builder-to-builder, engineer-to-engineer. Reduce
   the power asymmetry; do not grovel. Confidence, not desperation.
4. **Cognitive ease.** ≤75 words, one idea, short sentences, skimmable in seconds.
   Respect the 0.1s filter. No multi-paragraph pitch.
5. **One low-friction ask (commitment-consistency).** Ask for a small yes — a brief
   reply or a 15-minute chat — never "give me a job." Small commitments compound.
6. **Earned credibility, not name-dropping.** Reference at most one concrete, relevant
   proof point, only if it maps to *their* world. Relevance over résumé.
7. **Identity resonance.** Connect to something they actually identify with (their
   real work/mission), so the message feels addressed to *them*, not a segment.

**Hard prohibitions (the gate + writer both enforce):** no fabricated flattery, no
invented shared connections, no false urgency, no claims not traceable to evidence,
no flattery that isn't specific and true. If the only available message would violate
these, the gate should have already blocked it.

---

## 6. The candidate profile (use this REAL data — it makes the demo authentic)

Seed `profiles.py` `job_seeker` with the builder's actual background so the
intersection with AI/agent judges is genuine and strong:

- **Name:** Venkatesh Prasad Ravichandran. Goal: PM or AI Product role at a serious AI
  company. STEM OPT eligible (mention only if relevant).
- **Proof points (real, use as candidate_evidence):**
  - *Council of LLMs* — 7-phase multi-agent legal reasoning pipeline, ~23 model calls/
    query, 6-layer anti-hallucination, ~90% cost reduction via prompt caching; cited by
    a retired federal judge.
  - *Fred the Heretic* — production RAG system, ~80% stylistic alignment (expert-validated).
  - *Coalition Restoration Ops Platform* — AI automation: 70% manual email-triage
    reduction, 40% admin-overhead cut, zero post-launch defects.
  - Identity: "a PM who can build and an engineer who thinks in products."
- **relevance_criteria (strict):** a real reason exists only if the target builds /
  hires for / influences AI product, agent, or RAG work that these proof points map
  onto. Shared generic interest in "AI" is NOT enough. The overlap must be concrete.

Keep the existing `roofing` and `ceramic_coating` profiles for the context-switch.
**The agents must stay 100% domain-agnostic** — all domain knowledge lives in the
profile dict; swapping the dropdown changes behavior with zero code change. Prove this
in the demo.

---

## 7. Build plan — sequenced increments with VERIFY gates (do them in order)

> Get the keys yourself first (~15 min): ANTHROPIC_API_KEY (hackathon credits),
> Langfuse public+secret keys, Composio API key (optional), ClickHouse Cloud conn
> string (optional). Put them in `.env`. Claude Code: never enter credentials into
> signup forms — tell the user exactly what to fetch and where to paste it.

**INCREMENT 0 — Boot the existing app (15 min).**
Run it with the real key. Confirm a pass case and a refusal case both work end to end.
**VERIFY:** server starts, one strong target passes, one irrelevant target is held. Commit.

**INCREMENT 1 — Add the Intersection agent + the "what they work on" input (40 min).**
Add `intersect_agent` (§4) between research and verify. Add a `what_they_work_on`
free-text field to the UI and request body; make it the primary research grounding.
Make the gate score primarily off `overlap_strength`. Surface `primary_overlap` in the
UI verdict panel as the hero line.
**VERIFY:** type "Gagan, MTS at Anthropic, works on agents" → gate PASSES, primary
overlap names the multi-agent connection, message opens on that specific overlap.
Type "homeowner who just mows their lawn" under roofing → gate HOLDS. Commit.

**INCREMENT 2 — Demo reliability hardening (35 min) — DO NOT SKIP.**
Implement §8 in full: timeouts, fail-closed verifier, no-raw-errors, DEMO_MODE with
low temperature and a seeded fallback for the canonical judge inputs.
**VERIFY:** kill your network mid-run → UI shows a graceful state, never a stack trace.
Run the canonical "Anthropic agents" input 5x → passes every time with a coherent
overlap. Commit.

**INCREMENT 3 — Langfuse tracing (30 min).**
Wrap each of the 4–5 agent `_call`s with Langfuse `@observe`/spans. Name spans
`research`, `intersect`, `verify`, `write`. Confirm traces show the gate's decision.
**VERIFY:** a run appears in the Langfuse dashboard with all spans + token counts. Commit.

**INCREMENT 4 — Deploy to Render (20 min).**
Use `render.yaml`. Connect the repo, set env vars in the dashboard, deploy.
**VERIFY:** the live public URL runs a full pass + refusal end to end. Commit.

**INCREMENT 5 — Composio live enrichment (60 min, HARD TIMEBOX) — only if 0–4 done.**
Wire Composio web/LinkedIn lookup inside `fetch_target_context()` as **additive**
enrichment behind the 4s timeout. If it fights you, **revert and keep the typed-context
path** — that path already makes the demo work. Do not let this destabilize anything.
**VERIFY:** enrichment adds real facts when it works; when disabled, app is unchanged. Commit.

**INCREMENT 6 — ClickHouse decision log + one analytics view (45 min) — only if ahead.**
Append every verdict (target, role, score, send/block, overlap_strength, primary_overlap,
timestamp) to a ClickHouse table. Add one read view: block-rate by overlap_strength.
**VERIFY:** runs write rows; the view returns "found N → cleared M" style numbers. Commit.

**INCREMENT 7 — Polish + submission assets (45 min, PROTECT THIS TIME).**
Tighten copy/spacing, record the 2-min video to the §2 choreography, write the submission
(repo, live URL, video, the §1 pitch + the §9 sponsor sentence). Submit with ≥20 min buffer.

> Anything below the line you reach gets cut. Order is value-first on purpose.

---

## 8. Demo reliability engineering (the make-or-break details)

- **Timeouts:** any enrichment/web call wrapped in a 4s timeout; total run budget 12s.
  On timeout, proceed with what's gathered. Never hang the UI.
- **Fail closed:** if the verifier output won't parse, default `send=false` with a
  clean verdict_line. Safe direction for an anti-spam system, and never crashes.
- **No raw errors:** wrap every endpoint; on exception return a structured friendly
  payload the UI renders as "couldn't complete — try again," not a 500 trace.
- **DEMO_MODE (env flag):**
  - temperature low (≈0.2) for repeatable outputs;
  - a small seeded cache keyed on normalized canonical inputs (e.g. the few judge
    profiles you might demo) so that if a live call fails *during the pitch*, a
    pre-validated result still renders. This is a safety net, not the default path —
    label it clearly in code and only trigger on live failure.
- **Loading states:** show "researching → finding overlap → checking the gate" stage
  text so 8–12s feels intentional, not frozen.
- **Idempotent + cheap to re-run:** the presenter may run the same input twice; it must
  behave identically and quickly.
- **Pre-flight script:** a `make demo-check` / `python preflight.py` that runs the 3
  canonical inputs (judge-pass, irrelevant-hold, niche-switch) and prints PASS/FAIL so
  you can verify the whole demo in 30s right before going on stage.

---

## 9. Sponsor integrations (mapped — do the high-leverage ones, skip the rest)

- **Anthropic (Claude):** brains of every agent. Sonnet for intersect/verify/write;
  Haiku acceptable for research to save latency. (core)
- **Langfuse:** trace all agent calls → the "auditable agent" story made visible.
  Increment 3. (commit)
- **Render:** hosting. Increment 4. (commit)
- **Composio:** live research enrichment via the one hook. Increment 5, additive only. (commit if stable)
- **ClickHouse:** verdict decision-log + analytics. Increment 6, only if ahead. (stretch)
- **Guild.ai (flagship $2,800):** not an integration — the whole "agent that refuses to
  act" system is the entry. Lead the pitch here.
- **OpenUI / others:** below the cut line. Do NOT build unless everything else is done.

**The one-sentence sponsor story:** *"An agent crew that acts (Composio), shows its
reasoning (Langfuse), logs why it refuses at scale (ClickHouse), ships live (Render) —
built around one idea: an agent allowed to say no (Guild)."*

---

## 10. Guardrails / anti-goals (read before you "improve" anything)

- **Do not over-engineer.** No auth, no DB migrations framework, no multi-page app, no
  queue, no microservices. One FastAPI app + one HTML page. Every added dependency is
  a new way the demo breaks.
- **Do not make the critical path depend on a flaky external call.** Typed context is
  the spine; enrichment is a limb.
- **Do not let the gate block a judge in the match segment.** Refusal is demoed with an
  intentionally irrelevant target only.
- **Privacy/ethics:** only use information the target volunteers or that is clearly
  public. No scraping private data, no compiling dossiers from sensitive sources. The
  message must be something you'd be comfortable the recipient seeing was AI-assisted.
- **Truth over persuasion:** if the psychology spec and the truth ever conflict, truth
  wins — the gate exists to enforce exactly that.
- **Protect submission time.** A working demo submitted beats a better demo that missed
  the deadline.

---

## 11. Definition of Done (submission checklist)

- [ ] Live Render URL runs a full pass + refusal + niche-switch end to end.
- [ ] Canonical "Anthropic agents" input passes 5/5 with a coherent primary overlap.
- [ ] Irrelevant target reliably HELD (the refusal moment works).
- [ ] Context dropdown switches niche with zero code change (prove domain-agnostic).
- [ ] Message obeys the Relevance Psychology spec (≤75 words, specific hook, low-friction ask, all claims sourced).
- [ ] No raw error can reach the screen; preflight script passes 3/3.
- [ ] Langfuse shows traces; Render deployed. (ClickHouse/Composio if reached.)
- [ ] 2-min video recorded to the §2 choreography.
- [ ] Submission: repo + live URL + video + the §1 problem stat + §9 sponsor sentence.

---

## 12. How to drive me (Claude Code) — for the human

- Paste this file as `CLAUDE.md` at the repo root; I'll read it as standing context.
- Give me **one increment at a time** from §7. After each, I stop at its VERIFY gate;
  you confirm it works before we continue. Tight, ordered, verifiable — not one big sweep.
- Tell me which keys you've put in `.env` before the increment that needs them.
- If I start expanding scope or adding dependencies not in this brief, stop me and point
  me back to §10.
- Commit after every passing VERIFY so we always have a working fallback to demo.

**First command to give me:** "Read CLAUDE.md, then do INCREMENT 0 and stop at the VERIFY gate."
