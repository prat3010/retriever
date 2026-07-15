from src.domain.abstractions.config import ModelPricing
from src.domain.abstractions.inference import Usage


def calculate_cost(usage: Usage, model: str, pricing: dict[str, ModelPricing]) -> float:
    model_pricing = pricing.get(model)
    if not model_pricing or (model_pricing.input_cost_per_1k == 0 and model_pricing.output_cost_per_1k == 0):
        return 0.0
    input_cost = usage.input_tokens * model_pricing.input_cost_per_1k / 1000
    output_cost = usage.output_tokens * model_pricing.output_cost_per_1k / 1000
    return round(input_cost + output_cost, 6)
