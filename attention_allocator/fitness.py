from typing import Dict
from .models import ProductCandidate, Config


def compute_fitness(candidate: ProductCandidate, config: Config) -> float:
    """
    Placeholder heuristic: combine demand, effort, and competition into [0,1].
    You can refine this with real signals (signups, CTR, preorders).
    """
    signals: Dict = candidate.signals or {}
    demand = float(signals.get("demand_score", 0.5))  # 0-1
    competition = float(signals.get("competition_score", 0.5))  # 0-1 (lower better)
    effort_penalty = min(candidate.effort_hours_est / 20.0, 1.5)  # >1 if >20h

    # Explicit human-cycle friction.
    # Later you can swap these weights based on observed reality.
    handoff_cycles = max(0, int(getattr(candidate, "handoff_count", 0)))
    handoff_time_hours = max(0.0, float(getattr(candidate, "handoff_time_sec", 0.0))) / 3600.0
    handoff_penalty = 1.0 + 0.15 * handoff_cycles + 0.10 * handoff_time_hours

    base = 0.6 * demand + 0.3 * (1.0 - competition)
    fitness = (base / effort_penalty) / handoff_penalty
    return max(0.0, min(fitness, 1.0))
