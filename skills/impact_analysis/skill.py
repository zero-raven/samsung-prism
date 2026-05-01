"""Skill 3 — RAG-Based Impact Analysis using ChromaDB + LLM."""

import json
from dataclasses import dataclass

import anthropic
import chromadb


@dataclass
class ImpactReport:
    event: str
    entities: dict
    historical_analogue: str
    sector_impact: str
    confidence: str
    time_horizon: str
    reasoning: str


ANALYSIS_PROMPT = """You are a financial analyst. Given a current event and historical analogues, produce a structured impact analysis.

CURRENT EVENT: {event}
ENTITIES: {entities}
HISTORICAL ANALOGUES:
{analogues}

Return JSON only:
{{
  "historical_analogue": "most relevant analogue summary",
  "sector_impact": "which sectors affected and how",
  "confidence": "high|medium|low",
  "time_horizon": "short-term|medium-term|long-term",
  "reasoning": "step-by-step causal chain from event to impact"
}}"""


class ImpactAnalysisSkill:
    def __init__(self, api_key: str | None = None, chroma_path: str = "./data/chroma_db"):
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self.chroma = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.chroma.get_or_create_collection("historical_analogues")

    def add_historical_event(self, event_id: str, description: str, metadata: dict | None = None):
        self.collection.add(
            ids=[event_id],
            documents=[description],
            metadatas=[metadata or {}],
        )

    def analyze(self, event_title: str, entities: dict) -> ImpactReport:
        results = self.collection.query(query_texts=[event_title], n_results=3)
        analogues = "\n".join(results["documents"][0]) if results["documents"][0] else "No historical analogues found."

        if not self.client:
            raise RuntimeError("Anthropic API key not configured")

        resp = self.client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": ANALYSIS_PROMPT.format(
                event=event_title, entities=json.dumps(entities), analogues=analogues
            )}],
        )
        data = json.loads(resp.content[0].text)
        return ImpactReport(
            event=event_title,
            entities=entities,
            historical_analogue=data.get("historical_analogue", ""),
            sector_impact=data.get("sector_impact", ""),
            confidence=data.get("confidence", ""),
            time_horizon=data.get("time_horizon", ""),
            reasoning=data.get("reasoning", ""),
        )
