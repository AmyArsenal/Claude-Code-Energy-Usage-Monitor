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
    # Each reference is a natural phrase template: "{N} {name}".
    # Wh/unit sources and derivations are documented in METHODOLOGY.md.
    EnergyReference("Google searches", 0.3, "search", "searches"),
    EnergyReference("seconds of microwave", 0.28, "second", "seconds"),
    EnergyReference("minutes of LED light", 0.17, "minute", "minutes"),
    EnergyReference("iPhone charges", 15.0, "charge", "charges"),
    EnergyReference("hours of laptop use", 50.0, "hour", "hours"),
    EnergyReference("cups of tea boiled", 35.0, "cup", "cups"),
    EnergyReference("hours of ceiling fan", 75.0, "hour", "hours"),
    EnergyReference("hours of Netflix", 80.0, "hour", "hours"),
    EnergyReference("slices of toast", 30.0, "slice", "slices"),
    EnergyReference("miles of EV driving", 250.0, "mile", "miles"),
    EnergyReference("days of home use (US avg)", 30000.0, "day", "days"),
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
    return f"{num_str} {ref.name}"


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
