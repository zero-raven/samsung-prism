"""Skill 5 — Prediction Engine: Structured LLM reasoning for directional predictions."""

import json
from dataclasses import dataclass

import anthropic


@dataclass
class Prediction:
    ticker: str
    direction: str
    confidence: str
    horizon: str
    basis: str
    risk_flags: list[str]


PREDICTION_PROMPT = """You are a financial prediction analyst. Given the context below, predict the likely price direction for each affected ticker.

EVENT: {event}
HISTORICAL ANALOGUES: {analogues}
AFFECTED TICKERS: {tickers}
SECTOR IMPACT: {sector_impact}

For each ticker, return a JSON array:
[{{
  "ticker": "SYMBOL",
  "direction": "up|down|neutral",
  "confidence": "high|medium|low",
  "horizon": "1-3 days|1-2 weeks|1-3 months",
  "basis": "reasoning for this prediction",
  "risk_flags": ["list of risk factors that could invalidate this"]
}}]

Return JSON array only."""


class PredictionEngineSkill:
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def predict(self, event: str, analogues: str, tickers: list[str], sector_impact: str) -> list[Prediction]:
        if not self.client:
            raise RuntimeError("Anthropic API key not configured")

        resp = self.client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": PREDICTION_PROMPT.format(
                event=event, analogues=analogues,
                tickers=", ".join(tickers), sector_impact=sector_impact,
            )}],
        )
        data = json.loads(resp.content[0].text)
        return [Prediction(**p) for p in data]
