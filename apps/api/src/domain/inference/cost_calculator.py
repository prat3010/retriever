from src.domain.abstractions.config import ModelPricing
from src.domain.abstractions.inference import Usage


def calculate_cost(usage: Usage, model: str, pricing: dict[str, ModelPricing]) -> float:
    model_pricing = pricing.get(model)
    if not model_pricing and "/" in model:
        # Try lookup without provider prefix
        stripped = model.split("/")[-1]
        model_pricing = pricing.get(stripped)
    if not model_pricing:
        # Try lookup with common provider prefixes
        for prefix in ["openai/", "anthropic/", "gemini/"]:
            if prefix + model in pricing:
                model_pricing = pricing[prefix + model]
                break

    if not model_pricing or (model_pricing.input_cost_per_1k == 0 and model_pricing.output_cost_per_1k == 0):
        return 0.0
    input_cost = usage.input_tokens * model_pricing.input_cost_per_1k / 1000
    output_cost = usage.output_tokens * model_pricing.output_cost_per_1k / 1000
    return round(input_cost + output_cost, 6)
