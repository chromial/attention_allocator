import random
from typing import List
from .models import GAState, Config, ProductCandidate
from .fitness import compute_fitness
from .handoff import emit_handoff


def plan_phase(state: GAState, config: Config) -> None:
    # Compute fitness for all
    for cand in state.population:
        cand.fitness_score = compute_fitness(cand, config)

    # Rank by fitness
    state.population.sort(key=lambda c: c.fitness_score, reverse=True)

    # Select a small batch to validate this generation
    batch_size = min(3, len(state.population))
    state.validation_batch_ids = [c.id for c in state.population[:batch_size]]

    # Tiny cockpit log: fitness + signals + effort vs payoff
    print(f"\nGeneration {state.generation} plan: top candidates")
    for c in state.population[: min(3, len(state.population))]:
        sig = c.signals or {}
        visitors = sig.get("visitors")
        signups = sig.get("signups")
        print(
            "- "
            f"fitness={c.fitness_score:.3f} "
            f"price=${c.price:.0f} effort={c.effort_hours_est:.1f}h "
            f"signals(visitors={visitors}, signups={signups}) "
            f"handoff={c.handoff_count}x "
            f"niche={c.niche} format={c.format}"
        )


def act_phase(state: GAState, config: Config) -> None:
    id_set = set(state.validation_batch_ids or [])
    for cand in state.population:
        if cand.id in id_set:
            # Count the human cycle explicitly as a cost dimension
            cand.handoff_count += 1
            emit_handoff(cand)


def observe_phase(state: GAState, config: Config) -> None:
    # Recompute fitness after humans update signals in state.json
    for cand in state.population:
        cand.fitness_score = compute_fitness(cand, config)
    state.population.sort(key=lambda c: c.fitness_score, reverse=True)

    # Quick readout after the reload
    if state.population:
        best = state.population[0]
        print(
            f"\nObservation: best now fitness={best.fitness_score:.3f} "
            f"price=${best.price:.0f} effort={best.effort_hours_est:.1f}h "
            f"handoff={best.handoff_count}x time={best.handoff_time_sec:.0f}s "
            f"id={best.id}"
        )


def critique_phase(state: GAState, config: Config) -> None:
    if not state.population:
        return

    best = state.population[0]
    if state.best_candidate is None or best.fitness_score > state.best_candidate.fitness_score:
        state.best_candidate = best
        state.no_improvement_generations = 0
    else:
        state.no_improvement_generations += 1

    survivors = state.population[: max(2, len(state.population) // 2)]
    children: List[ProductCandidate] = []

    while len(survivors) + len(children) < config.population_size:
        p1, p2 = random.sample(survivors, 2)
        c1, c2 = crossover_products(p1, p2, config)
        mutate_product(c1, config)
        mutate_product(c2, config)
        children.extend([c1, c2])

    state.population = (survivors + children)[: config.population_size]
    state.generation += 1

    # This batch is “done”; next plan_phase will create a new one.
    state.validation_batch_ids = []


def crossover_products(p1: ProductCandidate, p2: ProductCandidate, config: Config):
    if random.random() > config.crossover_rate:
        return p1, p2
    child1 = ProductCandidate.new(
        niche=p1.niche,
        format=p2.format,
        problem=p1.problem,
        solution_outline=p2.solution_outline,
        price=p1.price,
        effort_hours_est=p1.effort_hours_est,
        maintenance_hours_est=p2.maintenance_hours_est,
    )
    child2 = ProductCandidate.new(
        niche=p2.niche,
        format=p1.format,
        problem=p2.problem,
        solution_outline=p1.solution_outline,
        price=p2.price,
        effort_hours_est=p2.effort_hours_est,
        maintenance_hours_est=p1.maintenance_hours_est,
    )
    return child1, child2


def mutate_product(c: ProductCandidate, config: Config) -> None:
    if random.random() < config.mutation_rate:
        c.price *= random.choice([0.8, 0.9, 1.1, 1.25])
        c.price = round(max(5.0, min(c.price, 500.0)), 2)


def exit_condition(state: GAState, config: Config) -> bool:
    from math import isfinite

    if state.best_candidate and isfinite(state.best_candidate.fitness_score):
        if state.best_candidate.fitness_score >= config.min_fitness_to_build:
            # You may refine this to use real revenue estimates
            pass

    if state.generation >= config.max_generations:
        return True
    if state.no_improvement_generations >= config.plateau_generations:
        return True
    return False
