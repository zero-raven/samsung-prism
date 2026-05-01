"""Skill 2 — Entity Extraction: Companies, countries, commodities, regulators, event type, sector."""

import json
from dataclasses import dataclass

import anthropic


@dataclass
class ExtractedEntities:
    companies: list[str]
    countries: list[str]
    commodities: list[str]
    regulators: list[str]
    event_type: str
    sectors: list[str]
    raw_title: str


EXTRACTION_PROMPT = """Extract structured entities from this news article.
Return JSON only, no markdown fences.

Article title: {title}
Article content: {content}

Return this exact JSON structure:
{{
  "companies": ["list of company names"],
  "countries": ["list of countries"],
  "commodities": ["list of commodities mentioned"],
  "regulators": ["list of regulatory bodies"],
  "event_type": "one of: earnings|policy|geopolitical|commodity|regulatory|macro|other",
  "sectors": ["list of affected sectors"]
}}"""


class EntityExtractionSkill:
    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def extract(self, title: str, content: str) -> ExtractedEntities:
        if not self.client:
            raise RuntimeError("Anthropic API key not configured")

        resp = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(title=title, content=content)}],
        )
        data = json.loads(resp.content[0].text)
        return ExtractedEntities(
            companies=data.get("companies", []),
            countries=data.get("countries", []),
            commodities=data.get("commodities", []),
            regulators=data.get("regulators", []),
            event_type=data.get("event_type", "other"),
            sectors=data.get("sectors", []),
            raw_title=title,
        )
