from __future__ import annotations

import time

from .models import ProductCandidate


def emit_handoff(candidate: ProductCandidate) -> None:
    """
    Print a HANDOFF block for this candidate.
    You will paste/translate this into your actual workflow.
    """
    print("🛑 HANDOFF CHECKPOINT\n")
    print(f"What needs to be done: Deploy validation for candidate {candidate.id}")
    print(
        f"Why it's needed: We are testing demand for an evergreen product in the niche "
        f"'{candidate.niche}' with format '{candidate.format}'."
    )
    print("\nHow to do it:")
    print("1. Create or duplicate a landing page on your chosen stack (Hostinger/Notion/etc).")
    print("2. Insert the following problem/solution copy:")
    print(f"   Problem: {candidate.problem}")
    print(f"   Solution: {candidate.solution_outline}")
    print("3. Connect a waitlist form (MailerLite/Substack) capturing email + one survey question.")
    print("4. Share the link via your chosen channel(s) (newsletter, social, DM, etc).")
    print("\nConfirmation required:")
    print("- Unique visitors")
    print("- Email signups")
    print("- Any qualitative feedback (replies, comments, DMs)")
    print("\nNext steps after confirmation:")
    print(
        "- Update this candidate's 'signals' in state.json "
        "(visitors, signups, notes).\n"
        "- Rerun main.py so the agent can recompute fitness, re-rank, "
        "and decide whether to build, kill, or iterate this idea."
    )
    print()


def await_handoff(state_json_path: str = "state.json") -> float:
    """Explicitly pause the system for human validation + metric entry.

    Returns:
        elapsed seconds spent in the human loop.

    Why this exists:
        HANDOFF is a state transition that pauses the system. Making the pause
        explicit in code prevents stale-memory bugs and allows editing state.json
        in another process.
    """
    print("Awaiting human metrics update for this generation...")
    print(f"(Update metrics/signals in {state_json_path}, then return here.)")
    start = time.time()
    input("Press ENTER once metrics are recorded in state.json...")
    return time.time() - start
