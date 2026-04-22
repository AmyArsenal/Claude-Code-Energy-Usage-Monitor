"""Table views for daily and monthly statistics display.

This module provides UI components for displaying aggregated usage data
in table format using Rich library.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Removed theme import - using direct styles
from claude_monitor.core.fun_facts import (
    best_comparisons,
    format_wh,
    headline_comparison,
)
from claude_monitor.core.grid_intensity import get_intensity, wh_to_gco2
from claude_monitor.utils.formatting import format_currency, format_number

logger = logging.getLogger(__name__)


class TableViewsController:
    """Controller for table-based views (daily, monthly)."""

    def __init__(
        self,
        console: Optional[Console] = None,
        country: str = "US",
        show_cost: bool = False,
    ):
        """Initialize the table views controller.

        Args:
            console: Optional Console instance for rich output
            country: Country code for grid carbon intensity lookup
            show_cost: Whether to include the legacy USD cost column
        """
        self.console = console
        self.country = country
        self.show_cost = show_cost
        # Define simple styles
        self.key_style = "cyan"
        self.value_style = "white"
        self.accent_style = "yellow"
        self.success_style = "green"
        self.energy_style = "bright_green"
        self.warning_style = "yellow"
        self.header_style = "bold cyan"
        self.table_header_style = "bold"
        self.border_style = "bright_blue"

    def _create_base_table(
        self, title: str, period_column_name: str, period_column_width: int
    ) -> Table:
        """Create a base table with common structure.

        Args:
            title: Table title
            period_column_name: Name for the period column ('Date' or 'Month')
            period_column_width: Width for the period column

        Returns:
            Rich Table object with columns added
        """
        table = Table(
            title=title,
            title_style="bold cyan",
            show_header=True,
            header_style="bold",
            border_style="bright_blue",
            expand=True,
            show_lines=True,
        )

        # Add columns — Cache Create + Cache Read collapsed into a single
        # "Cache" total to reduce horizontal crowding.
        table.add_column(
            period_column_name, style=self.key_style, width=period_column_width
        )
        table.add_column("Models", style=self.value_style, width=18)
        table.add_column("Input", style=self.value_style, justify="right", width=10)
        table.add_column("Output", style=self.value_style, justify="right", width=10)
        table.add_column("Cache", style=self.value_style, justify="right", width=10)
        table.add_column(
            "Total", style=self.accent_style, justify="right", width=12
        )
        table.add_column(
            "Energy", style=self.energy_style, justify="right", width=11
        )
        table.add_column(
            "CO2", style=self.energy_style, justify="right", width=9
        )
        if self.show_cost:
            table.add_column(
                "Cost", style=self.success_style, justify="right", width=10
            )

        return table

    def _add_data_rows(
        self, table: Table, data_list: List[Dict[str, Any]], period_key: str
    ) -> None:
        """Add data rows to the table.

        Args:
            table: Table to add rows to
            data_list: List of data dictionaries
            period_key: Key to use for period column ('date' or 'month')
        """
        for data in data_list:
            models_text = self._format_models(data["models_used"])
            total_tokens = (
                data["input_tokens"]
                + data["output_tokens"]
                + data["cache_creation_tokens"]
                + data["cache_read_tokens"]
            )

            energy_wh = data.get("total_energy_wh", 0.0)
            co2_g = wh_to_gco2(energy_wh, self.country)
            cache_total = (
                data["cache_creation_tokens"] + data["cache_read_tokens"]
            )
            row = [
                data[period_key],
                models_text,
                format_number(data["input_tokens"]),
                format_number(data["output_tokens"]),
                format_number(cache_total),
                format_number(total_tokens),
                format_wh(energy_wh),
                f"{co2_g:.1f} g",
            ]
            if self.show_cost:
                row.append(format_currency(data["total_cost"]))
            table.add_row(*row)

    def _add_totals_row(self, table: Table, totals: Dict[str, Any]) -> None:
        """Add totals row to the table.

        Args:
            table: Table to add totals to
            totals: Dictionary with total statistics
        """
        # Add totals row
        total_energy = totals.get("total_energy_wh", 0.0)
        total_co2 = wh_to_gco2(total_energy, self.country)
        total_cache = (
            totals.get("cache_creation_tokens", 0)
            + totals.get("cache_read_tokens", 0)
        )

        # Separator row with the right column count
        num_cols = 9 if self.show_cost else 8
        table.add_row(*[""] * num_cols)

        totals_row = [
            Text("Total", style=self.accent_style),
            "",
            Text(format_number(totals["input_tokens"]), style=self.accent_style),
            Text(format_number(totals["output_tokens"]), style=self.accent_style),
            Text(format_number(total_cache), style=self.accent_style),
            Text(format_number(totals["total_tokens"]), style=self.accent_style),
            Text(format_wh(total_energy), style=self.energy_style),
            Text(f"{total_co2:.1f} g", style=self.energy_style),
        ]
        if self.show_cost:
            totals_row.append(
                Text(format_currency(totals["total_cost"]), style=self.success_style)
            )
        table.add_row(*totals_row)

    def create_daily_table(
        self,
        daily_data: List[Dict[str, Any]],
        totals: Dict[str, Any],
        timezone: str = "UTC",
    ) -> Table:
        """Create a daily statistics table.

        Args:
            daily_data: List of daily aggregated data
            totals: Total statistics
            timezone: Timezone for display

        Returns:
            Rich Table object
        """
        # Create base table
        table = self._create_base_table(
            title=f"Claude Code Token Usage Report - Daily ({timezone})",
            period_column_name="Date",
            period_column_width=12,
        )

        # Add data rows
        self._add_data_rows(table, daily_data, "date")

        # Add totals
        self._add_totals_row(table, totals)

        return table

    def create_monthly_table(
        self,
        monthly_data: List[Dict[str, Any]],
        totals: Dict[str, Any],
        timezone: str = "UTC",
    ) -> Table:
        """Create a monthly statistics table.

        Args:
            monthly_data: List of monthly aggregated data
            totals: Total statistics
            timezone: Timezone for display

        Returns:
            Rich Table object
        """
        # Create base table
        table = self._create_base_table(
            title=f"Claude Code Token Usage Report - Monthly ({timezone})",
            period_column_name="Month",
            period_column_width=10,
        )

        # Add data rows
        self._add_data_rows(table, monthly_data, "month")

        # Add totals
        self._add_totals_row(table, totals)

        return table

    def create_summary_panel(
        self, view_type: str, totals: Dict[str, Any], period: str
    ) -> Panel:
        """Create a summary panel for the table view.

        Args:
            view_type: Type of view ('daily' or 'monthly')
            totals: Total statistics
            period: Period description

        Returns:
            Rich Panel object
        """
        # Create summary text
        total_energy = totals.get("total_energy_wh", 0.0)
        total_co2 = wh_to_gco2(total_energy, self.country)
        intensity = get_intensity(self.country)

        summary_lines = [
            f"{view_type.capitalize()} Usage Summary - {period}",
            "",
            f"Total Tokens:  {format_number(totals['total_tokens'])}",
            f"Total Energy:  {format_wh(total_energy)}",
            f"Total CO2:     {total_co2:.1f} g  "
            f"(grid: {self.country}, {intensity:.0f} gCO2/kWh)",
            f"Total Cost:    {format_currency(totals['total_cost'])}",
            f"Entries:       {format_number(totals['entries_count'])}",
        ]

        if total_energy > 0:
            summary_lines.append("")
            summary_lines.append("Your session used about the same as:")
            for line in best_comparisons(total_energy, count=3):
                summary_lines.append(f"  • {line}")
            summary_lines.append("")
            summary_lines.append(
                "(Energy estimates carry ~3x uncertainty. See METHODOLOGY.md.)"
            )

        summary_text = Text("\n".join(summary_lines), style=self.value_style)

        # Create panel
        panel = Panel(
            Align.center(summary_text),
            title="Summary",
            title_align="center",
            border_style=self.border_style,
            expand=False,
            padding=(1, 2),
        )

        return panel

    def _format_models(self, models: List[str]) -> str:
        """Format model names for display.

        Args:
            models: List of model names

        Returns:
            Formatted string of model names
        """
        if not models:
            return "No models"

        # Create bullet list
        if len(models) == 1:
            return models[0]
        elif len(models) <= 3:
            return "\n".join([f"• {model}" for model in models])
        else:
            # Truncate long lists
            first_two = models[:2]
            remaining_count = len(models) - 2
            formatted = "\n".join([f"• {model}" for model in first_two])
            formatted += f"\n• ...and {remaining_count} more"
            return formatted

    def create_no_data_display(self, view_type: str) -> Panel:
        """Create a display for when no data is available.

        Args:
            view_type: Type of view ('daily' or 'monthly')

        Returns:
            Rich Panel object
        """
        message = Text(
            f"No {view_type} data found.\n\nTry using Claude Code to generate some usage data.",
            style=self.warning_style,
            justify="center",
        )

        panel = Panel(
            Align.center(message, vertical="middle"),
            title=f"No {view_type.capitalize()} Data",
            title_align="center",
            border_style=self.warning_style,
            expand=True,
            height=10,
        )

        return panel

    def create_aggregate_table(
        self,
        aggregate_data: Union[List[Dict[str, Any]], List[Dict[str, Any]]],
        totals: Dict[str, Any],
        view_type: str,
        timezone: str = "UTC",
    ) -> Table:
        """Create a table for either daily or monthly aggregated data.

        Args:
            aggregate_data: List of aggregated data (daily or monthly)
            totals: Total statistics
            view_type: Type of view ('daily' or 'monthly')
            timezone: Timezone for display

        Returns:
            Rich Table object

        Raises:
            ValueError: If view_type is not 'daily' or 'monthly'
        """
        if view_type == "daily":
            return self.create_daily_table(aggregate_data, totals, timezone)
        elif view_type == "monthly":
            return self.create_monthly_table(aggregate_data, totals, timezone)
        else:
            raise ValueError(f"Invalid view type: {view_type}")

    def display_aggregated_view(
        self,
        data: List[Dict[str, Any]],
        view_mode: str,
        timezone: str,
        plan: str,
        token_limit: int,
        console: Optional[Console] = None,
    ) -> None:
        """Display aggregated view with table and summary.

        Args:
            data: Aggregated data
            view_mode: View type ('daily' or 'monthly')
            timezone: Timezone string
            plan: Plan type
            token_limit: Token limit for the plan
            console: Optional Console instance
        """
        if not data:
            no_data_display = self.create_no_data_display(view_mode)
            if console:
                console.print(no_data_display)
            else:
                print(no_data_display)
            return

        # Calculate totals
        totals = {
            "input_tokens": sum(d["input_tokens"] for d in data),
            "output_tokens": sum(d["output_tokens"] for d in data),
            "cache_creation_tokens": sum(d["cache_creation_tokens"] for d in data),
            "cache_read_tokens": sum(d["cache_read_tokens"] for d in data),
            "total_tokens": sum(
                d["input_tokens"]
                + d["output_tokens"]
                + d["cache_creation_tokens"]
                + d["cache_read_tokens"]
                for d in data
            ),
            "total_cost": sum(d["total_cost"] for d in data),
            "total_energy_wh": sum(d.get("total_energy_wh", 0.0) for d in data),
            "entries_count": sum(d.get("entries_count", 0) for d in data),
        }

        # Determine period for summary
        if view_mode == "daily":
            period = f"{data[0]['date']} to {data[-1]['date']}" if data else "No data"
        else:  # monthly
            period = f"{data[0]['month']} to {data[-1]['month']}" if data else "No data"

        # Create and display summary panel
        summary_panel = self.create_summary_panel(view_mode, totals, period)

        # Create and display table
        table = self.create_aggregate_table(data, totals, view_mode, timezone)

        # Display using console if provided
        if console:
            console.print(summary_panel)
            console.print()
            console.print(table)
        else:
            from rich import print as rprint

            rprint(summary_panel)
            rprint()
            rprint(table)
