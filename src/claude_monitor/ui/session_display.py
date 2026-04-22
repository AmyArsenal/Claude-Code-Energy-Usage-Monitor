"""Session display components for Claude Monitor.

Handles formatting of active session screens and session data display.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import pytz

from claude_monitor.core.fun_facts import (
    best_comparisons,
    format_wh,
    headline_comparison,
)
from claude_monitor.core.grid_intensity import get_intensity, wh_to_gco2
from claude_monitor.ui.components import CostIndicator, VelocityIndicator
from claude_monitor.ui.layouts import HeaderManager
from claude_monitor.ui.progress_bars import (
    ModelUsageBar,
    TimeProgressBar,
    TokenProgressBar,
)
from claude_monitor.utils.time_utils import (
    format_display_time,
    get_time_format_preference,
    percentage,
)


@dataclass
class SessionDisplayData:
    """Data container for session display information.

    This replaces the 21 parameters in format_active_session_screen method.
    """

    plan: str
    timezone: str
    tokens_used: int
    token_limit: int
    usage_percentage: float
    tokens_left: int
    elapsed_session_minutes: float
    total_session_minutes: float
    burn_rate: float
    session_cost: float
    per_model_stats: dict[str, Any]
    sent_messages: int
    entries: list[dict]
    predicted_end_str: str
    reset_time_str: str
    current_time_str: str
    show_switch_notification: bool = False
    show_exceed_notification: bool = False
    show_tokens_will_run_out: bool = False
    original_limit: int = 0
    session_energy_wh: float = 0.0
    country: str = "US"


class SessionDisplayComponent:
    """Main component for displaying active session information."""

    def __init__(self):
        """Initialize session display component with sub-components."""
        self.token_progress = TokenProgressBar()
        self.time_progress = TimeProgressBar()
        self.model_usage = ModelUsageBar()

    # Pulse frames for the energy emoji. Cycled based on wall time so the
    # icon animates across the Rich Live refresh ticks without needing
    # explicit tick counters.
    _PULSE_FRAMES = ["⚡", "✨", "💫", "⚡", "🔆", "✨"]

    def _pulse_icon(self) -> str:
        """Return the current pulse frame for the energy icon."""
        return self._PULSE_FRAMES[
            int(time.time() / 0.5) % len(self._PULSE_FRAMES)
        ]

    def _render_energy_block(
        self, energy_wh: float, country: str, width: int = 60
    ) -> list[str]:
        """Render an Energy Impact section with rotating fun facts.

        Layout::

            ─────── ⚡ ENERGY IMPACT · US grid, 380 gCO2/kWh ────────

              Session:  465 Wh            CO2:  177 g

              ≈ 5.8 Netflix hours streamed
              ≈ 13 cups of tea boiled   ·   27 iPhone charges

              ⓘ How is this calculated?  doc/METHODOLOGY.md
            ─────────────────────────────────────────────────────────

        Uses horizontal dividers only, which sidesteps the emoji/markup
        width math that breaks aligned vertical borders in Rich.
        """
        icon = self._pulse_icon()
        intensity = get_intensity(country)
        co2_g = wh_to_gco2(energy_wh, country)
        energy_str = format_wh(energy_wh)

        # Rotate primary fun fact every ~3s so the headline feels alive.
        comparisons = best_comparisons(energy_wh, count=5)
        if comparisons:
            idx = int(time.time() / 3) % len(comparisons)
            headline = comparisons[idx]
            remaining = [c for i, c in enumerate(comparisons) if i != idx]
        else:
            headline = headline_comparison(energy_wh)
            remaining = []

        # Compact header: `──── ⚡ ENERGY IMPACT · US grid, 380 gCO2/kWh ────`
        title_text = f" {icon} ENERGY IMPACT · {country} grid, {intensity:.0f} gCO2/kWh "
        # approximate visible length; emoji counts as 2
        approx_len = len(title_text) + 1
        dash_left = 4
        dash_right = max(3, width - dash_left - approx_len)
        header = (
            f"[separator]{'─' * dash_left}[/]"
            f"[bold]{title_text}[/bold]"
            f"[separator]{'─' * dash_right}[/]"
        )
        footer = f"[separator]{'─' * width}[/]"

        lines: list[str] = []
        lines.append(header)
        lines.append(
            f"  [value]Session:[/]  [bold warning]{energy_str}[/]"
            f"{' ' * max(2, 14 - len(energy_str))}"
            f"[value]CO2:[/]  [bold warning]{co2_g:,.1f} g[/]"
        )
        lines.append("")
        lines.append(f"  [info]≈ {headline}[/]")
        if remaining:
            # Show up to two extras, joined by · — truncate if too long
            extras = "   ·   ".join(remaining[:2])
            if len(extras) > width - 4:
                extras = remaining[0]
            lines.append(f"  [dim]≈ {extras}[/]")
        lines.append("")
        lines.append(
            "  [dim]ⓘ How is this calculated?  "
            "[cyan underline]doc/METHODOLOGY.md[/cyan underline][/dim]"
        )
        lines.append(footer)
        return lines

    def _render_wide_progress_bar(self, percentage: float) -> str:
        """Render a wide progress bar (50 chars) using centralized progress bar logic.

        Args:
            percentage: Progress percentage (can be > 100)

        Returns:
            Formatted progress bar string
        """
        from claude_monitor.terminal.themes import get_cost_style

        if percentage < 50:
            color = "🟢"
        elif percentage < 80:
            color = "🟡"
        else:
            color = "🔴"

        progress_bar = TokenProgressBar(width=50)
        bar_style = get_cost_style(percentage)

        capped_percentage = min(percentage, 100.0)
        filled = progress_bar._calculate_filled_segments(capped_percentage, 100.0)

        if percentage >= 100:
            filled_bar = progress_bar._render_bar(50, filled_style=bar_style)
        else:
            filled_bar = progress_bar._render_bar(
                filled, filled_style=bar_style, empty_style="table.border"
            )

        return f"{color} [{filled_bar}]"

    def format_active_session_screen_v2(self, data: SessionDisplayData) -> list[str]:
        """Format complete active session screen using data class.

        This is the refactored version using SessionDisplayData.

        Args:
            data: SessionDisplayData object containing all display information

        Returns:
            List of formatted lines for display
        """
        return self.format_active_session_screen(
            plan=data.plan,
            timezone=data.timezone,
            tokens_used=data.tokens_used,
            token_limit=data.token_limit,
            usage_percentage=data.usage_percentage,
            tokens_left=data.tokens_left,
            elapsed_session_minutes=data.elapsed_session_minutes,
            total_session_minutes=data.total_session_minutes,
            burn_rate=data.burn_rate,
            session_cost=data.session_cost,
            session_energy_wh=data.session_energy_wh,
            country=data.country,
            per_model_stats=data.per_model_stats,
            sent_messages=data.sent_messages,
            entries=data.entries,
            predicted_end_str=data.predicted_end_str,
            reset_time_str=data.reset_time_str,
            current_time_str=data.current_time_str,
            show_switch_notification=data.show_switch_notification,
            show_exceed_notification=data.show_exceed_notification,
            show_tokens_will_run_out=data.show_tokens_will_run_out,
            original_limit=data.original_limit,
        )

    def format_active_session_screen(
        self,
        plan: str,
        timezone: str,
        tokens_used: int,
        token_limit: int,
        usage_percentage: float,
        tokens_left: int,
        elapsed_session_minutes: float,
        total_session_minutes: float,
        burn_rate: float,
        session_cost: float,
        per_model_stats: dict[str, Any],
        sent_messages: int,
        entries: list[dict],
        predicted_end_str: str,
        reset_time_str: str,
        current_time_str: str,
        show_switch_notification: bool = False,
        show_exceed_notification: bool = False,
        show_tokens_will_run_out: bool = False,
        original_limit: int = 0,
        session_energy_wh: float = 0.0,
        country: str = "US",
        **kwargs,
    ) -> list[str]:
        """Format complete active session screen.

        Args:
            plan: Current plan name
            timezone: Display timezone
            tokens_used: Number of tokens used
            token_limit: Token limit for the plan
            usage_percentage: Usage percentage
            tokens_left: Remaining tokens
            elapsed_session_minutes: Minutes elapsed in session
            total_session_minutes: Total session duration
            burn_rate: Current burn rate
            session_cost: Session cost in USD
            per_model_stats: Model usage statistics
            sent_messages: Number of messages sent
            entries: Session entries
            predicted_end_str: Predicted end time string
            reset_time_str: Reset time string
            current_time_str: Current time string
            show_switch_notification: Show plan switch notification
            show_exceed_notification: Show exceed limit notification
            show_tokens_will_run_out: Show token depletion warning
            original_limit: Original plan limit

        Returns:
            List of formatted screen lines
        """

        screen_buffer = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        if plan in ["custom", "pro", "max5", "max20"]:
            from claude_monitor.core.plans import DEFAULT_COST_LIMIT

            cost_limit_p90 = kwargs.get("cost_limit_p90", DEFAULT_COST_LIMIT)
            messages_limit_p90 = kwargs.get("messages_limit_p90", 1500)

            screen_buffer.append("")
            if plan == "custom":
                screen_buffer.append("[bold]📊 Session-Based Dynamic Limits[/bold]")
                screen_buffer.append(
                    "[dim]Based on your historical usage patterns when hitting limits (P90)[/dim]"
                )
                screen_buffer.append(f"[separator]{'─' * 60}[/]")
            else:
                screen_buffer.append("")

            cost_percentage = (
                min(100, percentage(session_cost, cost_limit_p90))
                if cost_limit_p90 > 0
                else 0
            )
            cost_bar = self._render_wide_progress_bar(cost_percentage)
            screen_buffer.append(
                f"💰 [value]Cost Usage:[/]           {cost_bar} {cost_percentage:4.1f}%    [value]${session_cost:.2f}[/] / [dim]${cost_limit_p90:.2f}[/]"
            )
            screen_buffer.append("")

            token_bar = self._render_wide_progress_bar(usage_percentage)
            screen_buffer.append(
                f"📊 [value]Token Usage:[/]          {token_bar} {usage_percentage:4.1f}%    [value]{tokens_used:,}[/] / [dim]{token_limit:,}[/]"
            )
            screen_buffer.append("")

            messages_percentage = (
                min(100, percentage(sent_messages, messages_limit_p90))
                if messages_limit_p90 > 0
                else 0
            )
            messages_bar = self._render_wide_progress_bar(messages_percentage)
            screen_buffer.append(
                f"📨 [value]Messages Usage:[/]       {messages_bar} {messages_percentage:4.1f}%    [value]{sent_messages}[/] / [dim]{messages_limit_p90:,}[/]"
            )
            screen_buffer.append(f"[separator]{'─' * 60}[/]")

            time_percentage = (
                percentage(elapsed_session_minutes, total_session_minutes)
                if total_session_minutes > 0
                else 0
            )
            time_bar = self._render_wide_progress_bar(time_percentage)
            time_remaining = max(0, total_session_minutes - elapsed_session_minutes)
            time_left_hours = int(time_remaining // 60)
            time_left_mins = int(time_remaining % 60)
            screen_buffer.append(
                f"⏱️  [value]Time to Reset:[/]       {time_bar} {time_left_hours}h {time_left_mins}m"
            )
            screen_buffer.append("")

            if per_model_stats:
                model_bar = self.model_usage.render(per_model_stats)
                screen_buffer.append(f"🤖 [value]Model Distribution:[/]   {model_bar}")
            else:
                model_bar = self.model_usage.render({})
                screen_buffer.append(f"🤖 [value]Model Distribution:[/]   {model_bar}")
            screen_buffer.append(f"[separator]{'─' * 60}[/]")

            velocity_emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
            screen_buffer.append(
                f"🔥 [value]Burn Rate:[/]              [warning]{burn_rate:.1f}[/] [dim]tokens/min[/] {velocity_emoji}"
            )

            cost_per_min = (
                session_cost / max(1, elapsed_session_minutes)
                if elapsed_session_minutes > 0
                else 0
            )
            cost_per_min_display = CostIndicator.render(cost_per_min)
            screen_buffer.append(
                f"💲 [value]Cost Rate:[/]              {cost_per_min_display} [dim]$/min[/]"
            )

            if session_energy_wh > 0:
                screen_buffer.append("")
                screen_buffer.extend(
                    self._render_energy_block(session_energy_wh, country, width=62)
                )
        else:
            cost_display = CostIndicator.render(session_cost)
            cost_per_min = (
                session_cost / max(1, elapsed_session_minutes)
                if elapsed_session_minutes > 0
                else 0
            )
            cost_per_min_display = CostIndicator.render(cost_per_min)
            screen_buffer.append(f"💲 [value]Session Cost:[/]   {cost_display}")
            screen_buffer.append(
                f"💲 [value]Cost Rate:[/]      {cost_per_min_display} [dim]$/min[/]"
            )
            if session_energy_wh > 0:
                screen_buffer.append("")
                screen_buffer.extend(
                    self._render_energy_block(session_energy_wh, country, width=62)
                )
            screen_buffer.append("")

            token_bar = self.token_progress.render(usage_percentage)
            screen_buffer.append(f"📊 [value]Token Usage:[/]    {token_bar}")
            screen_buffer.append("")

            screen_buffer.append(
                f"🎯 [value]Tokens:[/]         [value]{tokens_used:,}[/] / [dim]~{token_limit:,}[/] ([info]{tokens_left:,} left[/])"
            )

            velocity_emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
            screen_buffer.append(
                f"🔥 [value]Burn Rate:[/]      [warning]{burn_rate:.1f}[/] [dim]tokens/min[/] {velocity_emoji}"
            )

            screen_buffer.append(
                f"📨 [value]Sent Messages:[/]  [info]{sent_messages}[/] [dim]messages[/]"
            )

            if per_model_stats:
                model_bar = self.model_usage.render(per_model_stats)
                screen_buffer.append(f"🤖 [value]Model Usage:[/]    {model_bar}")

            screen_buffer.append("")

            time_bar = self.time_progress.render(
                elapsed_session_minutes, total_session_minutes
            )
            screen_buffer.append(f"⏱️  [value]Time to Reset:[/]  {time_bar}")
            screen_buffer.append("")

        screen_buffer.append("")
        screen_buffer.append("🔮 [value]Predictions:[/]")
        screen_buffer.append(
            f"   [info]Tokens will run out:[/] [warning]{predicted_end_str}[/]"
        )
        screen_buffer.append(
            f"   [info]Limit resets at:[/]     [success]{reset_time_str}[/]"
        )
        screen_buffer.append("")

        self._add_notifications(
            screen_buffer,
            show_switch_notification,
            show_exceed_notification,
            show_tokens_will_run_out,
            original_limit,
            token_limit,
        )

        screen_buffer.append(
            f"⏰ [dim]{current_time_str}[/] 📝 [success]Active session[/] | [dim]Ctrl+C to exit[/] 🟢"
        )

        return screen_buffer

    def _add_notifications(
        self,
        screen_buffer: list[str],
        show_switch_notification: bool,
        show_exceed_notification: bool,
        show_tokens_will_run_out: bool,
        original_limit: int,
        token_limit: int,
    ) -> None:
        """Add notification messages to screen buffer.

        Args:
            screen_buffer: Screen buffer to append to
            show_switch_notification: Show plan switch notification
            show_exceed_notification: Show exceed limit notification
            show_tokens_will_run_out: Show token depletion warning
            original_limit: Original plan limit
            token_limit: Current token limit
        """
        notifications_added = False

        if show_switch_notification and token_limit > original_limit:
            screen_buffer.append(
                f"🔄 [warning]Token limit exceeded ({token_limit:,} tokens)[/]"
            )
            notifications_added = True

        if show_exceed_notification:
            screen_buffer.append(
                "⚠️  [error]You have exceeded the maximum cost limit![/]"
            )
            notifications_added = True

        if show_tokens_will_run_out:
            screen_buffer.append(
                "⏰ [warning]Cost limit will be exceeded before reset![/]"
            )
            notifications_added = True

        if notifications_added:
            screen_buffer.append("")

    def format_no_active_session_screen(
        self,
        plan: str,
        timezone: str,
        token_limit: int,
        current_time: Optional[datetime] = None,
        args: Optional[Any] = None,
    ) -> list[str]:
        """Format screen for no active session state.

        Args:
            plan: Current plan name
            timezone: Display timezone
            token_limit: Token limit for the plan
            current_time: Current datetime
            args: Command line arguments

        Returns:
            List of formatted screen lines
        """

        screen_buffer = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        empty_token_bar = self.token_progress.render(0.0)
        screen_buffer.append(f"📊 [value]Token Usage:[/]    {empty_token_bar}")
        screen_buffer.append("")

        screen_buffer.append(
            f"🎯 [value]Tokens:[/]         [value]0[/] / [dim]~{token_limit:,}[/] ([info]0 left[/])"
        )
        screen_buffer.append(
            "🔥 [value]Burn Rate:[/]      [warning]0.0[/] [dim]tokens/min[/]"
        )
        screen_buffer.append(
            "💲 [value]Cost Rate:[/]      [cost.low]$0.00[/] [dim]$/min[/]"
        )
        screen_buffer.append("📨 [value]Sent Messages:[/]  [info]0[/] [dim]messages[/]")
        screen_buffer.append("")

        if current_time and args:
            try:
                display_tz = pytz.timezone(args.timezone)
                current_time_display = current_time.astimezone(display_tz)
                current_time_str = format_display_time(
                    current_time_display,
                    get_time_format_preference(args),
                    include_seconds=True,
                )
                screen_buffer.append(
                    f"⏰ [dim]{current_time_str}[/] 📝 [info]No active session[/] | [dim]Ctrl+C to exit[/] 🟨"
                )
            except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
                screen_buffer.append(
                    "⏰ [dim]--:--:--[/] 📝 [info]No active session[/] | [dim]Ctrl+C to exit[/] 🟨"
                )
        else:
            screen_buffer.append(
                "⏰ [dim]--:--:--[/] 📝 [info]No active session[/] | [dim]Ctrl+C to exit[/] 🟨"
            )

        return screen_buffer
