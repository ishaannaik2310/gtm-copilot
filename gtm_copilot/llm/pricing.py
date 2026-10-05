"""Gemini model pricing table and cost calculation utility.

Prices are USD per 1 million tokens (as published by Google AI).
Update this table when Google revises pricing.

References:
  https://ai.google.dev/pricing
"""

from typing import Dict, Optional, Tuple


# (prompt_price_per_1m, completion_price_per_1m) in USD
_PRICING: Dict[str, Tuple[float, float]] = {
    # Gemini 2.5 series
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.5-flash-preview": (0.15, 0.60),
    # Gemini 2.0 series
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.0-flash-lite": (0.075, 0.30),
    # Gemini 1.5 series
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-flash-8b": (0.0375, 0.15),
    "gemini-1.5-pro": (1.25, 5.00),
    # Gemini 3.x series (experimental/preview, estimated)
    "gemini-3.5-flash": (0.15, 0.60),
    "gemini-3.6-flash": (0.15, 0.60),
    # flash-lite-latest alias (maps to 2.0-flash-lite pricing)
    "gemini-flash-lite-latest": (0.075, 0.30),
    "gemini-flash-lite": (0.075, 0.30),
}


def calculate_gemini_cost(
    model: str,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
) -> Optional[float]:
    """Calculate the estimated USD cost for a single Gemini API call.

    Args:
        model: Model identifier string (e.g. 'gemini-flash-lite-latest').
        prompt_tokens: Number of prompt/input tokens consumed.
        completion_tokens: Number of completion/output tokens generated.

    Returns:
        Estimated cost in USD, or None if the model is not in the pricing table
        or token counts are unavailable.
    """
    if prompt_tokens is None or completion_tokens is None:
        return None

    # Normalize model name: strip version suffixes like "-001" or "-exp-03-25"
    normalized = model.strip().lower()
    entry = _PRICING.get(normalized)

    if entry is None:
        # Try prefix matching: e.g. "gemini-2.0-flash-exp" → "gemini-2.0-flash"
        for key in _PRICING:
            if normalized.startswith(key):
                entry = _PRICING[key]
                break

    if entry is None:
        return None

    prompt_price_per_1m, completion_price_per_1m = entry
    cost = (prompt_tokens / 1_000_000) * prompt_price_per_1m + (
        completion_tokens / 1_000_000
    ) * completion_price_per_1m
    return round(cost, 8)
