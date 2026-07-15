import hashlib
import copy

from src.domain.abstractions.experiment import ExperimentConfig, VariantConfig
from src.domain.abstractions.config import TenantConfiguration


def _bucket(user_id: str | None, experiment_id: str, total: int = 100) -> int:
    seed = (user_id or "anon") + experiment_id
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return int(digest[:8], 16) % total


def assign_variant(
    user_id: str | None,
    experiment: ExperimentConfig,
) -> VariantConfig | None:
    if not experiment.variants:
        return None
    bucket = _bucket(user_id, experiment.id)
    cumulative = 0.0
    for v in experiment.variants:
        cumulative += v.traffic_pct
        if bucket < cumulative:
            return v
    return experiment.variants[-1]


def apply_overrides(
    config: TenantConfiguration,
    variant: VariantConfig,
) -> TenantConfiguration:
    if not variant.overrides:
        return config
    updated = config.model_copy(deep=True)
    for key, value in variant.overrides.items():
        parts = key.split(".")
        target = updated
        for part in parts[:-1]:
            target = getattr(target, part, None)
            if target is None:
                break
        if target is not None:
            setattr(target, parts[-1], value)
    return updated
