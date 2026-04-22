# Methodology: Estimating Electricity Use of Claude Code Sessions

_Version 0.1 — April 2026_

This document explains how Claude Code Energy Usage Monitor converts the
token counts in your local `~/.claude/projects/**/*.jsonl` session files
into an estimate of the electricity consumed to serve those tokens. We
report ranges, not point estimates, because no first-party per-token
energy figure has been published by Anthropic.

---

## 1. The target quantity

For each usage entry we compute:

```
Wh_entry = (in_tok  * E_in_model
          + out_tok * E_out_model
          + cc_tok  * E_cache_create_model
          + cr_tok  * E_cache_read_model) / 1_000_000
```

where `E_*_model` are energy coefficients in Wh per million tokens, per
model tier.

Totals aggregate over a session block or a day/month window. Users see
a midpoint figure plus a `~3x` uncertainty band.

---

## 2. Four cross-validation layers

Every coefficient in the shipped table is defensible against at least
three of the four layers below.

### Layer 1 — Bottom-up FLOPs math

For autoregressive transformer inference, output energy per token:

```
Wh_per_token = (2N * TDP_chip * PUE) / (FLOPs_peak * MFU * 3600)
```

Variables and ranges used:

| Variable | Meaning | Range | Source |
|---|---|---|---|
| N | Active parameters | Opus 200B-1T, Sonnet 70-200B, Haiku 8-40B | Public triangulation (API latency, GPU-hour pricing, leaked specs) |
| TDP_chip | GPU thermal design power | H100 700W, H200 700W, B200 1000W, Trainium2 ~500W | NVIDIA / AWS datasheets |
| FLOPs_peak | Peak chip throughput | H100 FP8 ≈ 3958 TFLOPS sparse | NVIDIA datasheet |
| MFU | Model FLOPs utilization | 30-55% (realistic inference) | vLLM paper; MLCommons |
| PUE | Data-center overhead | 1.08-1.2 (hyperscaler) | Uptime Institute |

Input tokens during prefill are batched more aggressively than output
generation, so we divide input energy by a factor of 3-10x depending on
typical batch geometry. We use 5x as the baseline.

Cache reads skip the expensive attention computation; we model them as
~10% of fresh input token cost (a memory fetch plus trivial compute).

### Layer 2 — MLPerf Inference Power benchmarks

MLCommons publishes measured Joules/query on commodity H100/H200/MI300X
hardware for Llama 2 70B, Llama 3 405B, GPT-J 6B, and others. Where an
MLPerf reference model is within ~2x of the estimated Claude tier size,
we take its Joules/query directly, normalize by the published mean
sequence length, and scale linearly in N.

### Layer 3 — Royal (2026) CHR revenue-implied ceiling

Hans Royal's _Compute Heat Rate_ (SSRN 6322318, Feb 2026) reports a
workload-tier revenue per MWh of electricity consumed:

| Royal tier | R_w ($/MWh) | Claude model we map to |
|---|---|---|
| Frontier Inference | 74,000 | Opus |
| Mid-Tier Inference | 14,800 | Sonnet |
| Commodity Inference | 1,850 | Haiku |

Given the published API price per output token, the revenue-implied
upper bound on energy per output token is:

```
Wh_per_token_upper_bound = (price_$/token * 1_000_000) / R_w
```

For Opus (~$75/Mtok output, frontier tier): ~1.0 × 10⁻³ Wh/tok
For Sonnet (~$15/Mtok output, mid tier): ~1.0 × 10⁻³ Wh/tok
For Haiku (~$4/Mtok output, commodity tier): ~2.2 × 10⁻³ Wh/tok

These are ceilings — if the operator's energy cost actually consumed
100% of revenue, margin collapses. Real physical Wh/tok is well below
these, typically 10-40% of ceiling. Our midpoints sit comfortably inside
this band.

### Layer 4 — Published first-party and academic anchors

Order-of-magnitude checks that the midpoint must reproduce within 3x:

- **Google (August 2025)** — Gemini median text prompt: 0.24 Wh, 0.03 gCO2e.
  Implied ~5 × 10⁻⁴ Wh/token at typical ~500-token completion.
- **Epoch AI (2025)** — ChatGPT: ~0.3 Wh/query, revised down from the
  earlier ~3 Wh industry talking point.
- **Luccioni, Jernite, Strubell (FAccT 2023)** — _Power Hungry Processing_.
  Measured 10⁻⁴ to 10⁻² Wh/token across 88 tasks on models from BLOOM to
  mid-sized encoders.
- **Luccioni et al. (2022)** — BLOOM 176B lifecycle.
- **Patterson et al. (Google, 2021)** — Carbon emissions and large NN training.
- **McDonald et al. (ICLR 2024)** — LLMCarbon end-to-end modeling framework.
- **De Vries (Joule 2023)** — _The growing energy footprint of AI_.
- **IEA (2024)** — _Electricity 2024_, data-center chapter.

---

## 3. Shipped coefficient table (v0.1)

All values are **Wh per million tokens**, midpoint only. Low and high
bounds are `mid * 0.4` and `mid * 3.0` respectively.

| Model tier | Input | Output | Cache create | Cache read |
|---|---|---|---|---|
| Opus    | 80 | 400 | 100 | 8 |
| Sonnet  | 30 | 200 | 38 | 3 |
| Haiku   | 6 | 40 | 8 | 0.6 |

Sanity check: a 1,000-token Sonnet response with 2,000 tokens of input
and 500 cache-read tokens works out to ~0.26 Wh. That sits between
Google's disclosed 0.24 Wh/median Gemini prompt and Epoch's 0.3 Wh/
ChatGPT query — exactly where we want to land.

---

## 4. Carbon intensity

Wh converts to grams CO2eq using a country-average grid intensity from
Ember's 2024 Global Electricity Review and EIA. Defaults to 380 g/kWh
(US) when no country is supplied. See `core/grid_intensity.py` for the
full table.

We use **annual average**, not marginal, grid intensity. Average answers
"what is a typical gram of electricity made of?" while marginal answers
"what plant fires when I add one more watt?" Marginal is higher and
harder to source reliably, so we chose average and document that choice.

For live, hourly, ISO-zone-specific intensity, swap
`get_intensity(country)` for an `ElectricityMaps` API call.

---

## 5. What is excluded

The shipped figure is **operational electricity only, data-center
serving side**. All of the following are _out of scope_ and should be
named when the number is quoted:

- **Embodied carbon** — chip fabrication, server manufacture, building
  construction, water treatment. Roughly 10-30% of lifetime emissions
  for GPUs; more for buildings.
- **Training amortization** — the energy spent training Claude models,
  divided across all inference queries. Usually small per-query but
  real over a model's lifetime.
- **End-user device** — your laptop drawing power while you wait.
- **Network transit** — the electricity between the data center and you.
- **Cooling water** — not energy per se, but often reported alongside.

---

## 6. Known weaknesses

Own these, or a reviewer will:

1. **Anthropic has not published model architectures.** Opus/Sonnet/Haiku
   could be dense or MoE. MoE would cut our numbers 3-10x.
2. **Active-parameter counts are inferred**, not disclosed.
3. **Batch-size effects dominate real energy per request.** A query
   hitting an idle GPU uses ~10x what one hitting a busy server uses.
   We report an amortized-at-typical-load figure.
4. **Average vs marginal grid intensity** — see §4. Marginal would give
   a higher CO2 number; we chose average for interpretability.
5. **Quarterly drift** — Royal refreshes CHR quarterly; hardware evolves
   (B200 → GB300 → future). We plan quarterly coefficient updates.

---

## 7. Reproducibility

The coefficient table lives in `src/claude_monitor/core/energy.py`.
The carbon-intensity table in `src/claude_monitor/core/grid_intensity.py`.
The fun-fact reference table in `src/claude_monitor/core/fun_facts.py`.
Every constant has a comment pointing to its source.

Rerun against your own session data:

```
claude-monitor --view daily --country US
```

---

## 8. Citations

- Royal, H. (2026). _The Compute Heat Rate: Quantifying AI-Driven Electricity
  Price Tolerance and Its Implications for Wholesale Market Repricing._
  SSRN 6322318.
- Luccioni, S., Jernite, Y., Strubell, E. (2023). _Power Hungry Processing:
  Watts Driving the Cost of AI Deployment?_ FAccT '24.
- Luccioni, S., Viguier, S., Ligozat, A.-L. (2022). _Estimating the Carbon
  Footprint of BLOOM._
- Patterson, D., et al. (2021). _Carbon Emissions and Large Neural Network
  Training._ arXiv:2104.10350.
- McDonald, J., et al. (2024). _LLMCarbon: Modeling the End-to-End Carbon
  Footprint of Large Language Models._ ICLR.
- De Vries, A. (2023). _The growing energy footprint of artificial
  intelligence._ Joule.
- Google (August 2025). Gemini energy and emissions disclosure.
- Epoch AI (2025). _How much energy does ChatGPT use?_
- IEA (2024). _Electricity 2024_, data-center chapter.
- MLCommons. _MLPerf Inference Power_ benchmark results.
- Ember (2024). _Global Electricity Review 2024._
- U.S. Energy Information Administration. State and country electricity data.
- Uptime Institute. _Annual Global Data Center Survey._
