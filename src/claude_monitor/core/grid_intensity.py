"""Grid carbon intensity by country.

Static table of grid-average CO2 intensity in gCO2eq per kWh. Values are
2024 annual averages from Ember's Global Electricity Review and the EIA.
See METHODOLOGY.md for sourcing notes. These are country averages, not
marginal or hourly — for a live value per ISO zone use ElectricityMaps.

Average is preferred here because most users want "what's the typical
footprint of my session," not "what's the marginal plant firing right now."
"""

from typing import Dict

# gCO2eq / kWh, 2024 country averages
GRID_INTENSITY_GCO2_PER_KWH: Dict[str, float] = {
    "US": 380.0,
    "USA": 380.0,
    "CA": 130.0,
    "CANADA": 130.0,
    "UK": 220.0,
    "GB": 220.0,
    "DE": 380.0,
    "GERMANY": 380.0,
    "FR": 60.0,
    "FRANCE": 60.0,
    "NO": 30.0,
    "NORWAY": 30.0,
    "SE": 50.0,
    "SWEDEN": 50.0,
    "IN": 700.0,
    "INDIA": 700.0,
    "CN": 580.0,
    "CHINA": 580.0,
    "JP": 470.0,
    "JAPAN": 470.0,
    "AU": 520.0,
    "AUSTRALIA": 520.0,
    "BR": 100.0,
    "BRAZIL": 100.0,
    "PL": 660.0,
    "POLAND": 660.0,
    "RU": 450.0,
    "RUSSIA": 450.0,
    "ZA": 750.0,
    "SOUTH_AFRICA": 750.0,
    "KR": 430.0,
    "SOUTH_KOREA": 430.0,
    "MX": 400.0,
    "MEXICO": 400.0,
    "ES": 160.0,
    "SPAIN": 160.0,
    "IT": 260.0,
    "ITALY": 260.0,
    "NL": 270.0,
    "NETHERLANDS": 270.0,
    "WORLD": 480.0,
}

DEFAULT_COUNTRY = "US"


def get_intensity(country: str) -> float:
    """Return gCO2eq/kWh for a country code or name. Falls back to world avg."""
    if not country:
        return GRID_INTENSITY_GCO2_PER_KWH[DEFAULT_COUNTRY]
    key = country.strip().upper().replace(" ", "_")
    return GRID_INTENSITY_GCO2_PER_KWH.get(
        key, GRID_INTENSITY_GCO2_PER_KWH["WORLD"]
    )


def wh_to_gco2(wh: float, country: str = DEFAULT_COUNTRY) -> float:
    """Convert Wh to grams of CO2eq using country grid intensity."""
    return (wh / 1000.0) * get_intensity(country)
