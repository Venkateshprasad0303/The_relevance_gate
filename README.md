# The Relevance Gate

**An outreach agent crew that refuses to send unless it finds a real, evidence-backed
reason to contact someone.** Found many. Contact few. All of them true.

Generic cold outreach replies at ~3.4%; evidence-grounded, signal-based outreach
replies at 15–25% — a ~5× lift. Recipients skim and delete in ~0.1 seconds. Every
other outreach tool optimizes for volume and fakes personalization. We optimize for
**send-worthiness** — our headline feature is the message we *won't* send.

## How it works

Four isolated Claude agents. Retrieval, judgment, and generation are separated so
**the writer cannot talk the gate into sending** — the gate renders its verdict
before the writer exists.

```
RESEARCH   → sourced dossier from what the target SAID (typed context is the spine)
INTERSECT  → the genuine overlap between your proven work and their world, evidenced both ways
THE GATE   → independent verifier: score 0–100, send or HOLD; fails closed
WRITE      → only if cleared: ≤75 words, built solely on the verified overlap
```

The agents are 100% domain-agnostic — all domain knowledge lives in a profile dict.
Switch the context dropdown (job seeker → roofing → ceramic coating) and the same
engine serves a different trade with zero code change.

## Run it

```
pip install -r requirements.txt
# .env: ANTHROPIC_API_KEY=...   (optional: CLICKHOUSE_HOST / CLICKHOUSE_PASSWORD)
uvicorn main:app --port 8000
```

Pre-stage check (runs the 3 canonical demo inputs, prints PASS/FAIL):

```
python preflight.py
```

## Reliability engineering

- Structured outputs (JSON-schema-enforced) on every agent call — no parse roulette.
- The gate **fails closed**: if the verdict can't be produced, nothing sends.
- Code-level enforcement: the writer never runs on weak/no overlap, regardless of
  what any model says.
- Per-stage timeouts; full run budget ~12s; no raw error ever reaches the screen.
- `DEMO_MODE`: low temperature, plus a clearly-labeled seeded fallback that only
  triggers if a live call fails mid-pitch.

## Sponsors

An agent crew with Claude as the brain of every agent (**Anthropic**), logging why it
refuses at scale (**ClickHouse** decision-log + block-rate analytics), shipping live
(**Render**) — built around one idea: an agent allowed to say no (**Guild**).
