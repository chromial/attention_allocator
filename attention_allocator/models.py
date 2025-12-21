from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import uuid


@dataclass
class ProductCandidate:
    id: str
    niche: str
    format: str
    problem: str
    solution_outline: str
    price: float
    effort_hours_est: float
    maintenance_hours_est: float
    signals: Dict[str, Any] = field(default_factory=dict)
    fitness_score: float = 0.0

    # Human-cycle friction (explicit time + cycle cost)
    # These start at zero and are updated whenever a candidate is handed off.
    handoff_count: int = 0
    handoff_time_sec: float = 0.0

    @staticmethod
    def new(**kwargs: Any) -> "ProductCandidate":
        return ProductCandidate(id=str(uuid.uuid4()), **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProductCandidate":
        return ProductCandidate(**data)

    def to_pretty_str(self) -> str:
        return (
            f"[{self.id}]\n"
            f"Niche: {self.niche}\nFormat: {self.format}\nProblem: {self.problem}\n"
            f"Solution: {self.solution_outline}\nPrice: {self.price}\n"
            f"Effort: {self.effort_hours_est}h, Maintenance: {self.maintenance_hours_est}h/mo\n"
            f"Signals: {self.signals}\nFitness: {self.fitness_score:.3f}\n"
            f"Handoff: {self.handoff_count}x, {self.handoff_time_sec:.0f}s"
        )


@dataclass
class Config:
    target_monthly_revenue: float = 600.0
    population_size: int = 12
    max_generations: int = 20
    plateau_generations: int = 3
    min_fitness_to_build: float = 0.75
    crossover_rate: float = 0.7
    mutation_rate: float = 0.2

    @staticmethod
    def default() -> "Config":
        return Config()


@dataclass
class GAState:
    generation: int
    population: List[ProductCandidate]
    best_candidate: Optional[ProductCandidate]
    no_improvement_generations: int

    # Explicit handoff tracking for this generation.
    # Store IDs (not objects) so state.json remains clean and stable.
    validation_batch_ids: List[str] = field(default_factory=list)

    @staticmethod
    def initial_from_seed(seed_path: Path, limit: int = 25) -> "GAState":
        """Create an initial GAState by loading a Top-25 seed list from disk.

        Seed format: JSONL (one JSON object per line) matching ProductCandidate fields.
        """
        if not seed_path.exists():
            raise FileNotFoundError(
                f"Seed file not found: {seed_path}. Run the upstream tournament rounds to produce Top-25 seeds."
            )

        population: List[ProductCandidate] = []
        for line_no, line in enumerate(seed_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_no} of {seed_path}: {e}") from e

            # Require stable IDs if present; otherwise generate one.
            if not data.get("id"):
                data["id"] = str(uuid.uuid4())

            population.append(ProductCandidate.from_dict(data))

            if len(population) >= limit:
                break

        if not population:
            raise ValueError(f"Seed file exists but contains no candidates: {seed_path}")

        return GAState(
            generation=0,
            population=population,
            best_candidate=None,
            no_improvement_generations=0,
            validation_batch_ids=[],
        )

    @staticmethod
    def initial() -> "GAState":
        # Backward-compatible empty state. Prefer initial_from_seed() for real runs.
        return GAState(
            generation=0,
            population=[],
            best_candidate=None,
            no_improvement_generations=0,
            validation_batch_ids=[],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "population": [c.to_dict() for c in self.population],
            "best_candidate": self.best_candidate.to_dict() if self.best_candidate else None,
            "no_improvement_generations": self.no_improvement_generations,
            "validation_batch_ids": list(self.validation_batch_ids),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GAState":
        pop = [ProductCandidate.from_dict(c) for c in data.get("population", [])]
        best = data.get("best_candidate")
        return GAState(
            generation=data.get("generation", 0),
            population=pop,
            best_candidate=ProductCandidate.from_dict(best) if best else None,
            no_improvement_generations=data.get("no_improvement_generations", 0),
            validation_batch_ids=data.get("validation_batch_ids", []) or [],
        )
