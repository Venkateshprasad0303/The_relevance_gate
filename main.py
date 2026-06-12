"""The Relevance Gate — FastAPI server.

One app, one page (CLAUDE.md §10). No raw error ever reaches the screen (§8).
The ClickHouse decision-log is env-gated and fire-and-forget: without
CLICKHOUSE_HOST the app behaves identically, and a logging failure can
never touch the demo path.
"""

import asyncio
import json
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents import build_profile_agent, fetch_url_text, run_pipeline
from profiles import PROFILES

load_dotenv()

app = FastAPI(title="The Relevance Gate")


# ------------------------------------------------- ClickHouse decision log

CH_HOST = os.getenv("CLICKHOUSE_HOST", "").strip().removeprefix("https://").rstrip("/")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
if CH_HOST and ":" not in CH_HOST:
    CH_HOST += ":8443"
CH_URL = f"https://{CH_HOST}/" if CH_HOST else ""

CH_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS relevance_verdicts (
    ts DateTime DEFAULT now(),
    profile_id String,
    target_name String,
    target_role String,
    score UInt8,
    send UInt8,
    overlap_strength String,
    primary_overlap String,
    verdict_line String
) ENGINE = MergeTree ORDER BY ts
"""


async def _ch(query: str, body: str = "") -> None:
    """One ClickHouse HTTPS call. Never raises — the log must not break the demo."""
    if not CH_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=3.0) as cx:
            await cx.post(
                CH_URL,
                params={"query": query},
                content=body.encode(),
                auth=("default", CH_PASSWORD),
            )
    except Exception:
        pass


@app.on_event("startup")
async def _init_clickhouse():
    await _ch(CH_TABLE_DDL)


def log_verdict(profile_id: str, target: dict, verdict: dict, intersection: dict | None):
    row = json.dumps({
        "profile_id": profile_id,
        "target_name": target.get("name", ""),
        "target_role": target.get("role", ""),
        "score": max(0, min(100, int(verdict.get("score", 0)))),
        "send": 1 if verdict.get("send") else 0,
        "overlap_strength": (intersection or {}).get("overlap_strength", ""),
        "primary_overlap": (intersection or {}).get("primary_overlap", {}).get("point", ""),
        "verdict_line": verdict.get("verdict_line", ""),
    })
    asyncio.create_task(_ch("INSERT INTO relevance_verdicts FORMAT JSONEachRow", row))


@app.get("/api/gate-stats")
async def gate_stats():
    """Block-rate by overlap strength — the 'refuses at scale' view (§7 inc. 6)."""
    if not CH_URL:
        return {"available": False, "rows": []}
    try:
        async with httpx.AsyncClient(timeout=3.0) as cx:
            r = await cx.post(
                CH_URL,
                params={"query": (
                    "SELECT overlap_strength, count() AS runs, "
                    "sum(send) AS cleared, runs - cleared AS held "
                    "FROM relevance_verdicts GROUP BY overlap_strength "
                    "ORDER BY runs DESC FORMAT JSON"
                )},
                auth=("default", CH_PASSWORD),
            )
            return {"available": True, "rows": r.json().get("data", [])}
    except Exception:
        return {"available": False, "rows": []}


# ---------------------------------------------------------------- run API

class RunRequest(BaseModel):
    profile_id: str
    name: str = ""
    role: str = ""
    what_they_work_on: str = ""
    link: str = ""
    search_web: bool = False


class ProfileRequest(BaseModel):
    material: str = ""  # pasted bio/résumé/company blurb, or a public URL
    goal: str = ""


@app.post("/api/build-profile")
async def build_profile(req: ProfileRequest):
    """Customization path: distill any sender — person or business — into a
    profile the domain-agnostic agents can run on."""
    try:
        material = req.material.strip()
        if material.startswith(("http://", "https://")):
            fetched = await fetch_url_text(material)
            if not fetched:
                return {"ok": False, "message":
                        "Couldn't read that page — login-walled sites like LinkedIn "
                        "block fetches. Paste the text of your profile instead."}
            material = fetched
        if len(material) < 40:
            return {"ok": False, "message":
                    "Give me a little more to work with — paste a bio, résumé, "
                    "or company blurb (or a public URL)."}
        built = await build_profile_agent(material, req.goal.strip())
        if req.goal.strip():
            built["candidate"]["goal"] = req.goal.strip()
        built["id"] = "custom"
        built["label"] = f"Custom — {built['candidate']['name']}"
        PROFILES["custom"] = built
        return {"ok": True, "id": "custom",
                "name": built["candidate"]["name"],
                "proof_points": len(built["proof_points"])}
    except Exception:
        return {"ok": False, "message": "Couldn't build the profile — try again."}


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@app.get("/api/profiles")
async def profiles():
    return [
        {
            "id": p["id"],
            "label": p["label"],
            "candidate": p["candidate"]["name"],
            "identity": p["candidate"]["identity"],
            "goal": p["candidate"]["goal"],
        }
        for p in PROFILES.values()
    ]


@app.post("/api/run")
async def run(req: RunRequest):
    profile = PROFILES.get(req.profile_id)
    target = {
        "name": req.name.strip() or "Unknown",
        "role": req.role.strip(),
        "what_they_work_on": req.what_they_work_on.strip(),
        "link": req.link.strip(),
        "search_web": req.search_web,
    }

    async def stream():
        if profile is None:
            yield _sse({"stage": "error", "status": "error",
                        "message": "Pick a context first, then run the gate."})
            return
        intersection = None
        try:
            async for event in run_pipeline(profile, target):
                if event["stage"] == "intersect" and event["status"] == "done":
                    intersection = event.get("data")
                if event["stage"] == "verify" and event["status"] == "done":
                    log_verdict(req.profile_id, target, event.get("data", {}), intersection)
                yield _sse(event)
        except Exception:
            # Final brace over run_pipeline's own handling — §8, no raw errors.
            yield _sse({"stage": "error", "status": "error",
                        "message": "Couldn't complete this run — try again."})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app.mount("/", StaticFiles(directory="static", html=True), name="static")
