# The Relevance Gate

**Job-hunt outreach that refuses to send unless it finds a real, evidence-backed
reason to contact someone.** Found many. Contact few. All of them true.

Generic cold outreach replies at ~3.4%; evidence-grounded, signal-based outreach
replies at 15–25% — a ~5× lift. Recruiters and hiring managers skim and delete in
~0.1 seconds. Every other tool optimizes for volume and fakes personalization. We
optimize for **send-worthiness** — the headline feature is the message we *won't*
send, because the message you don't send protects the ones you do.

**The loop:** paste your résumé (or a public URL) → it becomes your profile →
search the web for people worth reaching (hiring posts, founders building in your
specialty) → each candidate is researched, the genuine overlap with your proven
work is computed, and an independent gate scores whether you have a real opening
→ only then is a ≤75-word, evidence-grounded message written.

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

The agents are 100% profile-agnostic — all personal context lives in a profile dict.
Paste any résumé and the identical engine runs on that career with zero code change.

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
