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
    # Grouped: AI & crypto (topical), biological (surprising),
    # everyday (relatable), absurd (shareable). Sources below each line.
    #
    # -------- AI & crypto (topical context) --------
    EnergyReference("ChatGPT queries", 0.3, "query", "queries"),
    # Source: Epoch AI (2025) revised estimate for GPT-4o-class inference
    EnergyReference("Google searches (2009)", 0.3, "search", "searches"),
    # Source: Google's own 2009 disclosure; useful historical anchor
    EnergyReference("Ethereum transactions (post-Merge)", 30.0, "tx", "transactions"),
    # Source: Digiconomist / CCRI 2023; post-Merge proof-of-stake average
    EnergyReference("Bitcoin transactions", 800_000.0, "tx", "transactions"),
    # Source: Cambridge CBECI 2024 average per on-chain transaction
    #
    # -------- Biology (surprising, personal) --------
    EnergyReference("hours of your brain thinking", 20.0, "hour", "hours"),
    # Source: human brain metabolism ~20W at rest (Raichle 2002; well-cited)
    EnergyReference("hours of a person at rest", 100.0, "hour", "hours"),
    # Source: ~100W basal metabolic rate for an average adult
    EnergyReference("km of a human running", 80.0, "km", "km"),
    # Source: ~1 kcal/kg/km × 70kg × 4.184 kJ/kcal ≈ 81 Wh/km metabolic
    EnergyReference("house cats metabolising for a day", 80.0, "cat", "cats"),
    # Source: ~3.3W resting metabolic rate × 24h for a 4kg cat
    EnergyReference("beehives working for a day", 15.0, "hive", "hives"),
    # Source: colony foraging+thermoregulation; Seeley 1995 range
    #
    # -------- Everyday (relatable) --------
    EnergyReference("iPhone charges", 15.0, "charge", "charges"),
    # Source: iPhone 15 battery ~12 Wh + charging losses
    EnergyReference("hours of Wi-Fi router running", 10.0, "hour", "hours"),
    # Source: typical home router draws ~10W
    EnergyReference("hours of laptop use", 50.0, "hour", "hours"),
    # Source: typical laptop ~50W under active load
    EnergyReference("cups of tea boiled", 35.0, "cup", "cups"),
    # Source: 250mL × 4.18 J/g/K × 80K / 3600 = 23 Wh ideal + kettle losses
    EnergyReference("hours of ceiling fan", 75.0, "hour", "hours"),
    # Source: typical 75W residential ceiling fan
    EnergyReference("hours of Netflix streaming", 80.0, "hour", "hours"),
    # Source: IEA 2020 revised (~0.077 kWh/h incl device + network)
    EnergyReference("hours of gaming (PS5)", 180.0, "hour", "hours"),
    # Source: Sony PS5 system power measurements (~180W typical AAA game)
    EnergyReference("miles in a Tesla Model 3", 250.0, "mile", "miles"),
    # Source: EPA rated efficiency, ~250 Wh/mi
    #
    # -------- Absurd / memorable --------
    EnergyReference("hours of the Apollo Guidance Computer", 55.0, "hour", "hours"),
    # Source: NASA AGC spec: 55W total power draw during Apollo missions
    EnergyReference("dishwasher cycles", 1_800.0, "cycle", "cycles"),
    # Source: Energy Star typical modern dishwasher per cycle
    EnergyReference("loads of laundry (washer + dryer)", 2_500.0, "load", "loads"),
    # Source: ~500 Wh washer + ~2000 Wh electric dryer
    EnergyReference("days of home use (US avg)", 30_000.0, "day", "days"),
    # Source: EIA 2023 US residential average ~30 kWh/day
    EnergyReference("days of home use (India avg)", 3_000.0, "day", "days"),
    # Source: Central Electricity Authority India residential avg ~3 kWh/day
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
