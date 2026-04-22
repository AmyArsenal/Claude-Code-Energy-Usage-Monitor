"""Relatable energy comparisons.

Converts a Wh amount into human-relatable equivalents. Each reference is
sourced from a public spec or published figure; see METHODOLOGY.md for
citations.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EnergyReference:
    name: str
    wh_per_unit: float
    unit_singular: str
    unit_plural: str
    emoji: str = ""


REFERENCES: List[EnergyReference] = [
    # (name, Wh/unit, singular, plural, emoji)
    EnergyReference("Google searches", 0.3, "search", "searches", ""),
    EnergyReference("Microwave seconds at 1000W", 0.28, "second", "seconds", ""),
    EnergyReference("LED bulb minutes (10W)", 0.17, "minute", "minutes", ""),
    EnergyReference("Phone chargings (iPhone)", 15.0, "charge", "charges", ""),
    EnergyReference("Laptop hours (50W)", 50.0, "hour", "hours", ""),
    EnergyReference("Cups of tea boiled", 35.0, "cup", "cups", ""),
    EnergyReference("Ceiling fan hours (75W)", 75.0, "hour", "hours", ""),
    EnergyReference("Netflix hours streamed", 80.0, "hour", "hours", ""),
    EnergyReference("Toast slices", 30.0, "slice", "slices", ""),
    EnergyReference("EV miles (Tesla M3, 250 Wh/mi)", 250.0, "mile", "miles", ""),
    EnergyReference("Home kWh (US avg 30 kWh/day)", 1000.0, "kWh", "kWh", ""),
]


def best_comparisons(wh: float, count: int = 3) -> List[str]:
    """Pick the most relatable comparisons for a given Wh amount.

    Picks references where the resulting count lands between 0.5 and 500,
    then ranks by closeness to 10 (a comfortably human-relatable number).
    """
    if wh <= 0:
        return []

    scored = []
    for ref in REFERENCES:
        n = wh / ref.wh_per_unit
        if n < 0.5 or n > 500:
            continue
        # Prefer counts near 10 on a log scale
        import math
        score = abs(math.log10(n) - 1.0)
        scored.append((score, ref, n))

    scored.sort(key=lambda x: x[0])
    out = []
    for _, ref, n in scored[:count]:
        out.append(_format_comparison(ref, n))
    return out


def _format_comparison(ref: EnergyReference, n: float) -> str:
    if n >= 100:
        num_str = f"{n:,.0f}"
    elif n >= 10:
        num_str = f"{n:.0f}"
    elif n >= 1:
        num_str = f"{n:.1f}"
    else:
        num_str = f"{n:.2f}"
    unit = ref.unit_singular if abs(n - 1.0) < 0.05 else ref.unit_plural
    return f"{num_str} {unit} — {ref.name}"


def headline_comparison(wh: float) -> str:
    """Single-line summary for the summary panel."""
    picks = best_comparisons(wh, count=1)
    return picks[0] if picks else f"{wh:.2f} Wh"


def format_wh(wh: float) -> str:
    """Format Wh with sensible units."""
    if wh >= 1000:
        return f"{wh / 1000:.2f} kWh"
    if wh >= 1:
        return f"{wh:.2f} Wh"
    if wh >= 0.001:
        return f"{wh * 1000:.1f} mWh"
    return f"{wh * 1_000_000:.0f} uWh"
