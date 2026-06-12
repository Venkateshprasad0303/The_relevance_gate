"""Pre-flight: run the 3 canonical demo inputs and print PASS/FAIL (§8).
Run right before going on stage:  py preflight.py
"""

import asyncio
import sys
import time

from agents import run_pipeline
from profiles import PROFILES

CASES = [
    ("strong-pass", "job_seeker",
     {"name": "Gagan", "role": "MTS at Anthropic", "what_they_work_on": "I work on agents"},
     True),
    ("generic-hold", "job_seeker",
     {"name": "Alex", "role": "backend engineer at a regional bank",
      "what_they_work_on": "payment batch jobs; thinks AI is neat but doesn't work on it or hire for it"},
     False),
    ("irrelevant-hold", "job_seeker",
     {"name": "Sam", "role": "bakery owner",
      "what_they_work_on": "sourdough and weekend farmers markets"},
     False),
]


async def run_case(label, profile_id, target, expect_send):
    t0 = time.monotonic()
    verdict, msg, errored = None, None, False
    async for ev in run_pipeline(PROFILES[profile_id], target):
        if ev["stage"] == "verify" and ev["status"] == "done":
            verdict = ev["data"]
        if ev["stage"] == "write" and ev["status"] == "done":
            msg = ev["data"]
        if ev["stage"] == "error":
            errored = True
    elapsed = time.monotonic() - t0

    ok = not errored and verdict is not None and verdict["send"] == expect_send
    if ok and expect_send:
        ok = msg is not None and msg["word_count"] <= 75
    detail = "pipeline error" if errored else (
        f"send={verdict['send']} score={verdict['score']}"
        + (f" words={msg['word_count']}" if msg else "")
        + f" {elapsed:.1f}s"
    )
    print(f"{'PASS' if ok else 'FAIL'}  {label:<17} {detail}")
    return ok


async def main():
    results = await asyncio.gather(*(run_case(*c) for c in CASES))
    print("\nDEMO READY" if all(results) else "\nNOT READY — fix before stage")
    sys.exit(0 if all(results) else 1)


asyncio.run(main())
