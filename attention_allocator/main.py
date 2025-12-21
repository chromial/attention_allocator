from .models import GAState, Config
from .operators import plan_phase, act_phase, observe_phase, critique_phase, exit_condition
from .handoff import await_handoff

import json
import os
from pathlib import Path

STATE_PATH = Path("state/state.json")

# Top-25 seed file produced by the upstream tournament rounds (Round 3 finalists).
DEFAULT_SEED_FILE = "data/seed_candidates.round3_top25.jsonl"
SEED_PATH = Path(os.getenv("SEED_FILE", DEFAULT_SEED_FILE))


def _initial_state_from_seed() -> GAState:
    try:
        return GAState.initial_from_seed(SEED_PATH, limit=25)
    except Exception as e:
        raise SystemExit(
            f"Cannot start GA: failed to load Top-25 seed file at '{SEED_PATH}'.\n"
            f"Reason: {e}\n"
            f"Set SEED_FILE to a valid JSONL path (one candidate per line) and try again."
        ) from e


def load_state() -> GAState:
    if not STATE_PATH.exists():
        return _initial_state_from_seed()

    raw = STATE_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        # Common on fresh init: empty file created by `touch state.json`.
        return _initial_state_from_seed()

    try:
        data = json.loads(raw)
        return GAState.from_dict(data)
    except Exception:
        # Guardrail: avoid crashing on partial edits while iterating.
        return _initial_state_from_seed()


def save_state(state: GAState) -> None:
    STATE_PATH.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def main() -> None:
    config = Config.default()
    state = load_state()

    if not state.population:
        # With Top-25 seeding, this should only happen if the seed file is empty.
        print("Population is empty. Exiting.")
        return

    while not exit_condition(state, config):
        if not state.population:
            print("Population is empty. Terminating GA.")
            break

        plan_phase(state, config)

        # LOOP GUARD: if no validation batch exists, there's nothing to hand off.
        batch_ids = list(getattr(state, "validation_batch_ids", []) or [])
        if not batch_ids:
            print("No validation batch generated. Exiting to avoid infinite loop.")
            break

        act_phase(state, config)
        save_state(state)  # persist before handoff / waiting

        # HANDOFF is a state transition that pauses the system.
        # Make the pause explicit, then reload state to avoid stale-memory bugs.
        elapsed_sec = await_handoff(state_json_path=str(STATE_PATH))

        # Reload allows editing state.json in another process (and prevents stale reads).
        state = load_state()

        # Allocate the human-loop time to the candidates that were handed off.
        batch_ids = list(getattr(state, "validation_batch_ids", []) or [])
        if elapsed_sec > 0 and batch_ids:
            per_candidate = elapsed_sec / max(1, len(batch_ids))
            id_set = set(batch_ids)
            for c in state.population:
                if c.id in id_set:
                    c.handoff_time_sec += per_candidate

        observe_phase(state, config)
        critique_phase(state, config)
        save_state(state)

    print("GA finished.")
    if state.best_candidate is not None:
        print("Best candidate:")
        print(state.best_candidate.to_pretty_str())
    else:
        print("No best candidate selected.")


if __name__ == "__main__":
    main()
