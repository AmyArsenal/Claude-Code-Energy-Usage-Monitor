"""Print the full energy-derivation breakdown for the current session.

Invoked by `claude-energy-monitor --explain`. Reads recent JSONL entries,
finds the active session (or falls back to the most recent one), and
prints step-by-step math: tokens -> Wh -> CO2 -> fun facts. Also prints
the coefficient table and the sources each coefficient draws on.
"""

from __future__ import annotations

from typing import List

from claude_monitor.core.energy import EnergyCalculator
from claude_monitor.core.fun_facts import REFERENCES
from claude_monitor.core.grid_intensity import get_intensity, wh_to_gco2
from claude_monitor.data.analyzer import SessionAnalyzer
from claude_monitor.data.reader import load_usage_entries

METHODOLOGY_URL = (
    "https://github.com/AmyArsenal/Claude-Code-Energy-Usage-Monitor"
    "/blob/main/doc/METHODOLOGY.md"
)


def _rule(title: str = "", width: int = 72) -> str:
    if not title:
        return "─" * width
    dash_left = 4
    approx = len(title) + 2
    dash_right = max(3, width - dash_left - approx)
    return f"{'─' * dash_left} {title} {'─' * dash_right}"


def print_explain(country: str = "US", hours_back: int = 6) -> None:
    print(_rule("Claude Code Energy Monitor — Derivation"))
    print()

    entries, _ = load_usage_entries(hours_back=hours_back)
    if not entries:
        print("No recent usage data found. Run some Claude Code sessions first.")
        return

    analyzer = SessionAnalyzer()
    blocks = analyzer.transform_to_blocks(entries)
    active = [b for b in blocks if b.is_active and not b.is_gap]
    if not active:
        active = [b for b in blocks if not b.is_gap]
    if not active:
        print("No completed or active sessions found.")
        return

    b = active[-1]
    print(_rule("1. Token counts (read from ~/.claude/projects/**/*.jsonl)"))
    print()
    tc = b.token_counts
    total = tc.total_tokens
    rows = [
        ("Input tokens", tc.input_tokens),
        ("Output tokens", tc.output_tokens),
        ("Cache create", tc.cache_creation_tokens),
        ("Cache read", tc.cache_read_tokens),
    ]
    for name, val in rows:
        pct = (val / total * 100) if total else 0
        bar = "█" * int(pct / 2)
        print(f"  {name:<15} {val:>14,}   {pct:>5.1f}%  {bar}")
    print(f"  {'Total':<15} {total:>14,}")
    print()

    print(_rule("2. Per-model energy = tokens × Wh/Mtok coefficient"))
    print()
    ec = EnergyCalculator()
    grand_total = 0.0
    for model, stats in b.per_model_stats.items():
        coeffs = ec._get_coeffs_for_model(model)
        i_wh = stats["input_tokens"] / 1e6 * coeffs["input"]
        o_wh = stats["output_tokens"] / 1e6 * coeffs["output"]
        cc_wh = stats["cache_creation_tokens"] / 1e6 * coeffs["cache_creation"]
        cr_wh = stats["cache_read_tokens"] / 1e6 * coeffs["cache_read"]
        m_total = i_wh + o_wh + cc_wh + cr_wh
        grand_total += m_total
        print(f"  Model: {model}")
        print(
            f"    input  : {stats['input_tokens']:>12,} × {coeffs['input']:>6.1f}"
            f" / 1M = {i_wh:>9.3f} Wh"
        )
        print(
            f"    output : {stats['output_tokens']:>12,} × {coeffs['output']:>6.1f}"
            f" / 1M = {o_wh:>9.3f} Wh"
        )
        print(
            f"    cc     : {stats['cache_creation_tokens']:>12,} × "
            f"{coeffs['cache_creation']:>6.1f} / 1M = {cc_wh:>9.3f} Wh"
        )
        print(
            f"    cr     : {stats['cache_read_tokens']:>12,} × "
            f"{coeffs['cache_read']:>6.1f} / 1M = {cr_wh:>9.3f} Wh"
        )
        print(f"    ─── subtotal: {m_total:.2f} Wh")
        print()

    print(f"  TOTAL session energy: {grand_total:.2f} Wh")
    print()

    print(_rule("3. Coefficient table (Wh per million tokens)"))
    print()
    print(
        f"  {'Tier':<10} {'Input':>8} {'Output':>8} "
        f"{'Cache Create':>14} {'Cache Read':>12}"
    )
    for tier in ("opus", "sonnet", "haiku"):
        c = EnergyCalculator.FALLBACK_ENERGY[tier]
        print(
            f"  {tier:<10} {c['input']:>8.1f} {c['output']:>8.1f} "
            f"{c['cache_creation']:>14.1f} {c['cache_read']:>12.1f}"
        )
    print()
    print("  Each coefficient is the midpoint of four independent layers:")
    print("    1. Bottom-up FLOPs math: 2N × TDP × PUE / (FLOPs_peak × MFU × 3600)")
    print("    2. MLPerf Inference Power measured benchmarks on H100/H200")
    print("    3. Royal CHR revenue-implied ceiling (SSRN 6322318, Feb 2026)")
    print("    4. Google Gemini Aug-2025 disclosure: 0.24 Wh / median prompt")
    print()

    print(_rule(f"4. Wh -> grams CO2eq (grid: {country})"))
    print()
    intensity = get_intensity(country)
    co2_g = wh_to_gco2(grand_total, country)
    print(
        f"  CO2 = Wh / 1000 × gCO2/kWh = "
        f"{grand_total:.2f} / 1000 × {intensity:.0f} = {co2_g:.2f} g"
    )
    print()
    print("  For comparison — same Wh on other grids:")
    for cc in ("NO", "FR", "UK", "US", "CN", "IN"):
        g = wh_to_gco2(grand_total, cc)
        print(f"    {cc}: {get_intensity(cc):>4.0f} g/kWh  ->  {g:>7.1f} g CO2")
    print()

    print(_rule("5. Fun facts (session Wh / Wh-per-unit)"))
    print()
    shown = []
    not_shown = []
    for ref in REFERENCES:
        n = grand_total / ref.wh_per_unit
        line = (
            f"  {grand_total:.2f} / {ref.wh_per_unit:>7.2f} Wh "
            f"= {n:>12,.2f} {ref.name}"
        )
        if 0.5 <= n <= 500:
            shown.append(line + "   [shown in UI]")
        else:
            not_shown.append(line)
    for line in shown:
        print(line)
    print()
    print("  (Dropped — outside 0.5..500 'readable' range):")
    for line in not_shown:
        print(line)
    print()

    print(_rule("6. Uncertainty and known limitations"))
    print()
    print("  These numbers are midpoints. The real Wh carries roughly 3x")
    print("  uncertainty in either direction. Known biases likely making")
    print("  the midpoint HIGH:")
    print("    * AWS Trainium2 inference is 2-3x more efficient than H100")
    print("      (coefficient anchored to H100; Anthropic runs Trainium-heavy)")
    print("    * Speculative decoding likely ~halves output token energy")
    print("      (not modeled)")
    print("    * Cache-read coefficient (10% of input) is a guess; real")
    print("      value could be 3-5% for quantized KV-cache.")
    print()
    print("  Known biases likely making the midpoint LOW:")
    print("    * Parameter count for Opus inferred, could be higher")
    print("    * Batching at low-utilization periods burns idle GPU power")
    print("    * Embodied carbon (chip fab, DC construction) excluded")
    print()

    print(_rule("See methodology"))
    print()
    print(f"  {METHODOLOGY_URL}")
    print()
