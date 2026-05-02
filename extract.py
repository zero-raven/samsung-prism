"""
FinSight Skill 2 — Entity Extraction & Structuring
=====================================================
Processes pending articles through Gemini LLM for structured entity extraction.
Updates the knowledge graph with discovered entities and relationships.

═══════════════════════════════════════════════════════
INPUT:
    - data/queue/pending_articles.yaml    → Raw articles from Skill 1
    - data/graph/knowledge_graph.json     → Existing knowledge graph
    - config.yaml                         → Significance threshold, model settings

OUTPUT:
    - data/events/evt_<id>.yaml           → Structured events (significance ≥ threshold)
    - data/graph/knowledge_graph.json     → Updated graph with new entities/edges
    - data/logs/extract.log               → Processing log
    - data/logs/low_significance.log      → Events below threshold
    - data/queue/pending_articles.yaml    → Cleared after processing

TRIGGERS:
    - After Skill 1 (finsight-ingest) completes
    - Can be run manually: python extract.py
═══════════════════════════════════════════════════════
"""

import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config_loader import (
    load_config, get_workspace_path, read_yaml, write_yaml, append_to_log
)
from shared.llm_client import generate_yaml
from shared.graph_manager import GraphManager


EXTRACTION_PROMPT = """You are a financial news analyst. Extract structured entities from this news article.

Article Headline: "{headline}"
Article Summary: "{summary}"
Source: {source}

Extract the following and return ONLY valid YAML (no markdown fences, no extra text):

entities:
  companies:
    - list of company names mentioned (use full official names, e.g., "Reliance Industries" not "Reliance")
  sectors:
    - list from ONLY these options: energy, banking, IT, pharma, auto, FMCG, metals, realty, infrastructure, telecom, defence, media
  countries:
    - list of countries mentioned or implied
  commodities:
    - list if any mentioned: crude oil, natural gas, gold, silver, copper, steel, etc.
event_type: one of: geopolitical, regulatory, macroeconomic, earnings, supply_chain, central_bank, trade_policy, corporate_action
significance: integer 1-10 (based on: how many sectors affected, how major the entities are, how likely to move markets. 1=trivial, 10=market-moving crisis)
one_line_summary: a single sentence summarizing the market impact of this event

IMPORTANT RULES:
- significance 8-10: Major events (central bank decisions, trade wars, major corporate results, geopolitical crises)
- significance 5-7: Notable events (sector-specific news, mid-cap earnings, policy changes)
- significance 1-4: Routine events (minor corporate news, analyst opinions, market commentary)
- If the article is not financial/economic news, set significance to 1
- Always include at least one sector if the article is about markets
"""


def extract_entities_from_article(article: dict, config: dict) -> dict:
    """
    Extract structured entities from a single article using Gemini.

    INPUT:
        article — dict with keys: headline, summary, source
        config  — full config dict

    OUTPUT:
        dict — Extracted entities with keys: entities, event_type, significance, one_line_summary
    """
    model = config.get("llm", {}).get("extraction_model", "gemini-2.0-flash")

    prompt = EXTRACTION_PROMPT.format(
        headline=article.get("headline", ""),
        summary=article.get("summary", ""),
        source=article.get("source", "unknown"),
    )

    result = generate_yaml(prompt, model_name=model)

    # Validate and set defaults
    if "error" in result:
        return {
            "entities": {"companies": [], "sectors": [], "countries": [], "commodities": []},
            "event_type": "unknown",
            "significance": 1,
            "one_line_summary": article.get("headline", ""),
            "extraction_error": result.get("error"),
        }

    # Ensure all expected keys exist
    entities = result.get("entities", {})
    if not isinstance(entities, dict):
        entities = {"companies": [], "sectors": [], "countries": [], "commodities": []}

    for key in ["companies", "sectors", "countries", "commodities"]:
        if key not in entities or not isinstance(entities[key], list):
            entities[key] = []

    result["entities"] = entities
    result.setdefault("event_type", "unknown")
    result.setdefault("significance", 1)
    result.setdefault("one_line_summary", article.get("headline", ""))

    # Clamp significance to 1-10
    try:
        result["significance"] = max(1, min(10, int(result["significance"])))
    except (ValueError, TypeError):
        result["significance"] = 1

    return result


def run_extraction():
    """
    Main extraction pipeline.

    STEP 1: Load pending articles from queue
    STEP 2: For each article, call LLM for entity extraction
    STEP 3: Write significant events to data/events/
    STEP 4: Update knowledge graph
    STEP 5: Clear the pending queue
    """
    print("=" * 60)
    print("[Skill 2] FinSight Entity Extraction Starting...")
    print("=" * 60)

    config = load_config()
    threshold = config.get("thresholds", {}).get("significance_min", 5)

    # Step 1: Load pending articles
    queue_path = get_workspace_path("queue", "pending_articles.yaml")
    queue_data = read_yaml(queue_path)
    articles = queue_data.get("articles", [])

    if not articles:
        print("[Skill 2] No pending articles. Nothing to extract.")
        append_to_log("No pending articles to process.", "extract.log")
        return []

    print(f"[Skill 2] Processing {len(articles)} articles...")

    # Initialize knowledge graph
    graph = GraphManager()
    significant_events = []
    low_sig_count = 0

    # Step 2: Process each article
    for i, article in enumerate(articles):
        headline = article.get("headline", "Unknown")
        print(f"\n[Skill 2] [{i+1}/{len(articles)}] Extracting: {headline[:80]}...")

        try:
            extracted = extract_entities_from_article(article, config)
        except Exception as e:
            append_to_log(f"Extraction failed for '{headline}': {e}", "extract.log")
            print(f"  ✗ Extraction failed: {e}")
            continue

        significance = extracted.get("significance", 1)
        event_id = f"evt_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{i:03d}"

        # Build full event object
        event = {
            "event_id": event_id,
            "source_article": {
                "headline": article.get("headline"),
                "source": article.get("source"),
                "url": article.get("url"),
                "published": article.get("published"),
            },
            "entities": extracted.get("entities", {}),
            "event_type": extracted.get("event_type"),
            "significance": significance,
            "one_line_summary": extracted.get("one_line_summary"),
            "extracted_at": datetime.datetime.now().isoformat(),
        }

        # Step 3: Route based on significance
        if significance >= threshold:
            event_path = get_workspace_path("events", f"{event_id}.yaml")
            write_yaml(event_path, event)
            significant_events.append(event)
            print(f"  ✓ Significance {significance}/10 → Written to events/")
        else:
            low_sig_count += 1
            append_to_log(
                f"LOW_SIG ({significance}): {headline[:100]}", "low_significance.log"
            )
            print(f"  ○ Significance {significance}/10 → Logged (below threshold)")

        # Step 4: Update knowledge graph (for ALL events, even low significance)
        try:
            graph.update_from_extraction(event_id, extracted)
        except Exception as e:
            print(f"  ⚠ Graph update failed: {e}")

    # Save graph
    graph.save()
    graph_stats = graph.get_stats()

    # Step 5: Clear the queue
    write_yaml(queue_path, {"articles": [], "last_updated": datetime.datetime.now().isoformat()})

    summary = (
        f"Extracted {len(articles)} articles. "
        f"{len(significant_events)} significant (≥{threshold}), "
        f"{low_sig_count} below threshold. "
        f"Graph: {graph_stats['total_nodes']} nodes, {graph_stats['total_edges']} edges."
    )
    append_to_log(summary, "extract.log")
    print(f"\n[Skill 2] Done. {summary}")

    return significant_events


if __name__ == "__main__":
    from shared.config_loader import ensure_workspace
    ensure_workspace()
    events = run_extraction()
    print(f"\n[Skill 2] Returned {len(events)} significant events for analysis.")
