"""
FinSight Skill 3 — RAG-Based Impact Analysis
=======================================================
Replaces the iterative Hypothesize approach with Historical RAG.

Pipeline per event:
  1. Embed the event summary.
  2. Query ChromaDB for historical analogues, filtered by event_type.
  3. LLM synthesizes causal chain based on analogues.

INPUT:
    - data/events/evt_<id>.yaml
OUTPUT:
    - data/analysis/chain_<event_id>.yaml
"""

import sys
import os
import glob
import datetime
import chromadb
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.config_loader import (
    load_config, get_workspace_path, read_yaml, write_yaml, append_to_log
)
from shared.llm_client import generate_yaml

# Ensure ChromaDB setup
CHROMA_DB_DIR = get_workspace_path("chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name="historical_events")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

SYNTHESIS_PROMPT = """You are producing a causal impact analysis for a retail investor.

CURRENT EVENT: {event_summary}
EVENT TYPE: {event_type}
ENTITIES INVOLVED: {entities}

HISTORICAL ANALOGUES (Similar past events and their impact):
{analogues}

Based on the historical precedent above, produce a structured causal chain analysis for the CURRENT EVENT.
Return ONLY valid YAML:

causal_chain:
  trigger: "One sentence: what happened"
  mechanism: "2-3 sentences: HOW this event historically propagates through the market."
  affected_sectors:
    - sector: "sector name"
      direction: "positive or negative or neutral"
      magnitude: "high or medium or low"
      reasoning: "Why this sector is affected, citing the historical analogue."
  affected_companies:
    - name: "Company Name"
      ticker: "TICKER.NS"
      direction: "positive or negative"
      reasoning: "Specific reason from evidence"
  time_horizon: "immediate or short_term or medium_term or long_term"
  confidence: "HIGH or MEDIUM or LOW"
  key_risks:
    - "Specific factor that could make this time different"
  summary_for_investor: "2-3 sentence plain-English summary a retail investor can act on. No jargon."
"""

def seed_database():
    """Seed ChromaDB with the golden dataset if empty."""
    if collection.count() > 0:
        return
        
    print("[Skill 3] Seeding ChromaDB with historical events...")
    golden_data_path = get_workspace_path("historical_events.yaml")
    
    if not os.path.exists(golden_data_path):
        print(f"[Skill 3] Golden dataset not found at {golden_data_path}")
        return
        
    data = read_yaml(golden_data_path)
    events = data.get("events", [])
    
    for evt in events:
        text_to_embed = f"{evt['headline']} - {evt['event_type']}"
        embedding = embedder.encode(text_to_embed).tolist()
        
        collection.add(
            ids=[evt["event_id"]],
            embeddings=[embedding],
            documents=[str(evt)], # Store the YAML dict string representation as the document
            metadatas=[{"event_type": evt["event_type"], "direction": evt["direction"]}]
        )
    print(f"[Skill 3] Successfully seeded {len(events)} events.")


def analyze_event(event: dict, config: dict) -> dict:
    event_id = event.get("event_id", "unknown")
    event_summary = event.get("one_line_summary", event.get("headline", ""))
    event_type = event.get("event_type", "unknown")
    entities = event.get("entities", {})
    model = config.get("llm", {}).get("reasoning_model", "gemini-2.0-flash")

    print(f"\n  [Step 1] Retrieving historical analogues for: {event_summary}")
    
    # RAG Retrieval with Metadata Filtering
    query_embedding = embedder.encode(event_summary).tolist()
    
    # Try with strict filtering first
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        where={"event_type": event_type}
    )
    
    # Fallback to no filter if no results
    if not results['documents'][0]:
        print("  [Warning] No exact event_type match. Relaxing filters.")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )

    analogues_text = ""
    if results['documents'] and results['documents'][0]:
        for idx, doc in enumerate(results['documents'][0]):
            analogues_text += f"\n--- Analogue {idx+1} ---\n{doc}\n"
    else:
        analogues_text = "No direct historical analogues found."

    print(f"  [Step 2] Synthesizing causal chain via LLM...")
    
    entities_str = str(entities)

    synthesis_prompt = SYNTHESIS_PROMPT.format(
        event_summary=event_summary,
        event_type=event_type,
        entities=entities_str,
        analogues=analogues_text,
    )

    synthesis = generate_yaml(synthesis_prompt, model_name=model)
    causal_chain = synthesis.get("causal_chain", synthesis)

    analysis = {
        "event_id": event_id,
        "event_summary": event_summary,
        "event_type": event_type,
        "retrieved_analogues": results['documents'][0] if results['documents'] else [],
        "causal_chain": causal_chain,
        "analyzed_at": datetime.datetime.now().isoformat(),
        "model_used": model,
    }

    return analysis

def run_impact_analysis():
    print("=" * 60)
    print("[Skill 3] FinSight RAG Impact Analysis Starting...")
    print("=" * 60)

    config = load_config()
    seed_database()

    events_dir = get_workspace_path("events")
    analysis_dir = get_workspace_path("analysis")

    event_files = sorted(glob.glob(os.path.join(events_dir, "evt_*.yaml")))
    if not event_files:
        print("[Skill 3] No events to analyze.")
        append_to_log("No events to analyze.", "analyze.log")
        return []

    unprocessed = []
    for ef in event_files:
        event_id = os.path.splitext(os.path.basename(ef))[0]
        chain_path = os.path.join(analysis_dir, f"chain_{event_id}.yaml")
        if not os.path.exists(chain_path):
            unprocessed.append(ef)

    if not unprocessed:
        print("[Skill 3] All events already analyzed.")
        return []

    print(f"[Skill 3] Found {len(unprocessed)} unprocessed events")

    analyses = []
    for i, event_file in enumerate(unprocessed):
        event = read_yaml(event_file)
        event_id = event.get("event_id", os.path.splitext(os.path.basename(event_file))[0])
        headline = event.get("one_line_summary", event.get("source_article", {}).get("headline", "Unknown"))

        print(f"\n{'─' * 60}")
        print(f"[Skill 3] [{i+1}/{len(unprocessed)}] Analyzing: {headline[:70]}...")

        try:
            analysis = analyze_event(event, config)

            chain_path = get_workspace_path("analysis", f"chain_{event_id}.yaml")
            write_yaml(chain_path, analysis)
            analyses.append(analysis)

            confidence = analysis.get("causal_chain", {}).get("confidence", "UNKNOWN")
            print(f"  ✓ Analysis complete. Confidence: {confidence}")
            append_to_log(f"Analyzed {event_id} | Confidence: {confidence}", "analyze.log")
        except Exception as e:
            print(f"  ✗ Analysis failed: {e}")
            append_to_log(f"FAILED {event_id}: {e}", "analyze.log")

    print(f"\n[Skill 3] Done. Analyzed {len(analyses)}/{len(unprocessed)} events.")
    return analyses

if __name__ == "__main__":
    run_impact_analysis()
