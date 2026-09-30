"""Population projection from Census of India figures."""

# Greater Mumbai: 11,978,450 (Census 2001) -> 12,442,373 (Census 2011)
CITY_POP_2001 = 11_978_450
CITY_POP_2011 = 12_442_373
CITY_ANNUAL_GROWTH = (CITY_POP_2011 / CITY_POP_2001) ** (1 / 10) - 1  # ≈ 0.38 % per year


def project_population(pop_2011: int, year: int, annual_growth: float = CITY_ANNUAL_GROWTH) -> int:
    """Geometric projection with the documented 2001–2011 decadal CAGR (ward-level 2001 data is not open)."""
    return int(round(pop_2011 * (1 + annual_growth) ** (year - 2011)))
