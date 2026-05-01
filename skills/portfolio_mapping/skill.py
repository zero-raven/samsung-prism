"""Skill 4 — Portfolio Mapping: Map impacted sectors to user holdings."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Holding:
    ticker: str
    shares: int
    sector: str


@dataclass
class ExposureReport:
    affected_holdings: list[dict]
    total_exposed_tickers: int
    summary: str


class PortfolioMappingSkill:
    def __init__(self, portfolio_path: str = "./config/portfolio.yaml"):
        self.holdings = self._load_portfolio(portfolio_path)

    def _load_portfolio(self, path: str) -> list[Holding]:
        data = yaml.safe_load(Path(path).read_text())
        return [Holding(**h) for h in data.get("portfolio", [])]

    def map_exposure(self, impacted_sectors: list[str], sector_impact: str) -> ExposureReport:
        impacted_lower = {s.lower() for s in impacted_sectors}
        affected = []
        for h in self.holdings:
            if h.sector.lower() in impacted_lower:
                affected.append({"ticker": h.ticker, "shares": h.shares, "sector": h.sector})

        summary = f"{len(affected)} holding(s) exposed across sectors: {', '.join(impacted_sectors)}. {sector_impact}"
        return ExposureReport(
            affected_holdings=affected,
            total_exposed_tickers=len(affected),
            summary=summary,
        )
