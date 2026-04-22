"""Energy calculations for Claude models.

Estimates electricity consumption (Wh) of Claude Code sessions from token
counts, using per-model coefficients in Wh per million tokens. Structurally
mirrors PricingCalculator so the two run in parallel through the same pipeline.

The coefficients below are defensible midpoints derived from four
cross-validation layers (see doc/METHODOLOGY.md):

  1. Bottom-up FLOPs math: Wh/tok = 2N * TDP * PUE / (FLOPs_peak * MFU * 3600)
  2. MLPerf Inference Power benchmarks on H100/H200
  3. Royal (2026) CHR revenue-implied upper bound per workload tier
  4. Google Gemini disclosure (Aug 2025, ~0.24 Wh/median prompt) and
     Epoch AI (~0.3 Wh/ChatGPT query) as order-of-magnitude anchors

Every reported number is a midpoint. Real values carry roughly a 3x
uncertainty band in either direction; the tool surfaces ranges in the UI,
not point estimates.
"""

from typing import Any, Dict, Optional

from claude_monitor.core.models import CostMode, TokenCounts, normalize_model_name


class EnergyCalculator:
    """Calculates electricity usage (Wh) from token counts.

    Coefficients are Wh per million tokens, by model tier and token type.
    Tiers map to Royal (2026) CHR workload categories:
        Opus    -> Frontier Inference
        Sonnet  -> Mid-Tier Inference
        Haiku   -> Commodity Inference
    """

    # Wh per million tokens (midpoint estimates, v0.1).
    # Output tokens cost ~5x input because autoregressive generation
    # can't be batch-amortized like prefill. Cache reads are ~10x cheaper
    # than fresh input (memory fetch vs full prefill).
    FALLBACK_ENERGY: Dict[str, Dict[str, float]] = {
        "opus": {
            "input": 80.0,
            "output": 400.0,
            "cache_creation": 100.0,
            "cache_read": 8.0,
        },
        "sonnet": {
            "input": 30.0,
            "output": 200.0,
            "cache_creation": 38.0,
            "cache_read": 3.0,
        },
        "haiku": {
            "input": 6.0,
            "output": 40.0,
            "cache_creation": 8.0,
            "cache_read": 0.6,
        },
    }

    # Uncertainty multipliers for low/high bounds vs midpoint.
    # Reflects the combined spread of parameter count uncertainty,
    # MFU (30-55%), PUE (1.08-1.2), and hardware mix (Trainium vs H100/B200).
    UNCERTAINTY_LOW: float = 0.4
    UNCERTAINTY_HIGH: float = 3.0

    def __init__(
        self, custom_energy: Optional[Dict[str, Dict[str, float]]] = None
    ) -> None:
        self.energy: Dict[str, Dict[str, float]] = custom_energy or {
            "claude-3-opus": self.FALLBACK_ENERGY["opus"],
            "claude-3-sonnet": self.FALLBACK_ENERGY["sonnet"],
            "claude-3-haiku": self.FALLBACK_ENERGY["haiku"],
            "claude-3-5-sonnet": self.FALLBACK_ENERGY["sonnet"],
            "claude-3-5-haiku": self.FALLBACK_ENERGY["haiku"],
            "claude-sonnet-4-20250514": self.FALLBACK_ENERGY["sonnet"],
            "claude-opus-4-20250514": self.FALLBACK_ENERGY["opus"],
        }
        self._cache: Dict[str, float] = {}

    def calculate_energy(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        tokens: Optional[TokenCounts] = None,
        strict: bool = False,
    ) -> float:
        """Return midpoint energy consumption in Wh."""
        if model == "<synthetic>":
            return 0.0

        if tokens is not None:
            input_tokens = tokens.input_tokens
            output_tokens = tokens.output_tokens
            cache_creation_tokens = tokens.cache_creation_tokens
            cache_read_tokens = tokens.cache_read_tokens

        cache_key = (
            f"{model}:{input_tokens}:{output_tokens}:"
            f"{cache_creation_tokens}:{cache_read_tokens}"
        )
        if cache_key in self._cache:
            return self._cache[cache_key]

        coeffs = self._get_coeffs_for_model(model, strict=strict)

        wh = (
            (input_tokens / 1_000_000) * coeffs["input"]
            + (output_tokens / 1_000_000) * coeffs["output"]
            + (cache_creation_tokens / 1_000_000) * coeffs["cache_creation"]
            + (cache_read_tokens / 1_000_000) * coeffs["cache_read"]
        )

        wh = round(wh, 6)
        self._cache[cache_key] = wh
        return wh

    def energy_range(self, midpoint_wh: float) -> Dict[str, float]:
        """Return (low, mid, high) Wh for UI display."""
        return {
            "low": round(midpoint_wh * self.UNCERTAINTY_LOW, 6),
            "mid": round(midpoint_wh, 6),
            "high": round(midpoint_wh * self.UNCERTAINTY_HIGH, 6),
        }

    def _get_coeffs_for_model(
        self, model: str, strict: bool = False
    ) -> Dict[str, float]:
        normalized = normalize_model_name(model)

        if normalized in self.energy:
            return self.energy[normalized]
        if model in self.energy:
            return self.energy[model]

        if strict:
            raise KeyError(f"Unknown model: {model}")

        model_lower = model.lower()
        if "opus" in model_lower:
            return self.FALLBACK_ENERGY["opus"]
        if "haiku" in model_lower:
            return self.FALLBACK_ENERGY["haiku"]
        return self.FALLBACK_ENERGY["sonnet"]

    def calculate_energy_for_entry(
        self, entry_data: Dict[str, Any], mode: CostMode
    ) -> float:
        """Compute Wh for a single usage entry. Mirrors PricingCalculator."""
        model = entry_data.get("model") or entry_data.get("Model")
        if not model:
            raise KeyError("Missing 'model' key in entry_data")

        input_tokens = entry_data.get("inputTokens", 0) or entry_data.get(
            "input_tokens", 0
        )
        output_tokens = entry_data.get("outputTokens", 0) or entry_data.get(
            "output_tokens", 0
        )
        cache_creation = entry_data.get(
            "cacheCreationInputTokens", 0
        ) or entry_data.get("cache_creation_tokens", 0)
        cache_read = (
            entry_data.get("cacheReadInputTokens", 0)
            or entry_data.get("cache_read_input_tokens", 0)
            or entry_data.get("cache_read_tokens", 0)
        )

        return self.calculate_energy(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
        )
