"""Skill 3 — RAG-Based Impact Analysis using ChromaDB + LLM."""

import json
import os
import yaml
from dataclasses import dataclass

import chromadb
from sentence_transformers import SentenceTransformer


@dataclass
class ImpactReport:
    event: str
    entities: dict
    retrieved_analogues: list
    causal_chain: dict


ANALYSIS_PROMPT = """You are a financial analyst. Given a current event and historical analogues, produce a structured impact analysis.

CURRENT EVENT: {event}
EVENT TYPE: {event_type}
ENTITIES: {entities}

HISTORICAL ANALOGUES:
{analogues}

Based on the historical precedent above, produce a structured causal chain analysis for the CURRENT EVENT.
Return JSON only:
{{
  "causal_chain": {{
      "trigger": "One sentence: what happened",
      "mechanism": "2-3 sentences: HOW this event historically propagates through the market.",
      "affected_sectors": [
        {{
          "sector": "sector name",
          "direction": "positive or negative or neutral",
          "magnitude": "high or medium or low",
          "reasoning": "Why this sector is affected, citing the historical analogue."
        }}
      ],
      "time_horizon": "immediate or short_term or medium_term or long_term",
      "confidence": "HIGH or MEDIUM or LOW"
  }}
}}"""


class ImpactAnalysisSkill:
    def __init__(self, chroma_path: str = "./data/chroma_db", llm_client=None):
        self.chroma = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.chroma.get_or_create_collection("historical_events")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = llm_client  # Assuming the runner will pass the LM Studio/Anthropic client

    def seed_golden_dataset(self, yaml_path: str = "./data/historical_events.yaml"):
        """Seeds the database with curated historical events."""
        if self.collection.count() > 0:
            return  # Already seeded
            
        if not os.path.exists(yaml_path):
            print(f"Golden dataset not found at {yaml_path}")
            return
            
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
            
        events = data.get("events", [])
        for evt in events:
            text_to_embed = f"{evt['headline']} - {evt['event_type']}"
            embedding = self.embedder.encode(text_to_embed).tolist()
            
            self.collection.add(
                ids=[evt["event_id"]],
                embeddings=[embedding],
                documents=[json.dumps(evt)],
                metadatas=[{"event_type": evt["event_type"], "direction": evt["direction"]}]
            )

    def analyze(self, event_title: str, event_type: str, entities: dict) -> ImpactReport:
        # Step 1: Embed the query
        query_embedding = self.embedder.encode(event_title).tolist()

        # Step 2: Retrieve with metadata filtering
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            where={"event_type": event_type}
        )
        
        # Fallback if no exact event_type matches
        if not results['documents'] or not results['documents'][0]:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=3
            )

        analogues_text = ""
        analogues_list = []
        if results['documents'] and results['documents'][0]:
            for idx, doc in enumerate(results['documents'][0]):
                analogues_text += f"\n--- Analogue {idx+1} ---\n{doc}\n"
                analogues_list.append(doc)
        else:
            analogues_text = "No direct historical analogues found."

        # Step 3: Synthesis
        if not self.client:
            raise RuntimeError("LLM client not configured")
            
        # Call the LLM (abstracted based on client type)
        # We assume the client has a standard messages interface (like Anthropic/OpenAI)
        resp = self.client.messages.create(
            model="qwen2.5-7b-instruct-1m",  # Based on friend's README
            max_tokens=1024,
            messages=[{"role": "user", "content": ANALYSIS_PROMPT.format(
                event=event_title, 
                event_type=event_type, 
                entities=json.dumps(entities), 
                analogues=analogues_text
            )}],
        )
        
        data = json.loads(resp.content[0].text)
        
        return ImpactReport(
            event=event_title,
            entities=entities,
            retrieved_analogues=analogues_list,
            causal_chain=data.get("causal_chain", {})
        )
