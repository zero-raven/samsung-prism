"""
FinSight Skill 3 — Hypothesis-Driven Impact Analysis
=======================================================
The core intelligence skill. Replaces RAG with live investigation.

Pipeline per event:
  1. Query knowledge graph for prior context
  2. LLM generates 4 investigation directives
  3. Each directive executes targeted API calls
  4. LLM synthesizes all evidence into a causal chain

═══════════════════════════════════════════════════════
INPUT:
    - data/events/evt_<id>.yaml           → Structured event from Skill 2
    - data/graph/knowledge_graph.json     → Prior entity connections
    - config.yaml                         → Model settings

OUTPUT:
    - data/analysis/chain_<event_id>.yaml → Full causal chain + investigation results
    - data/logs/hypothesize.log           → Processing log

TRIGGERS:
    - After Skill 2 (finsight-extract) writes events
    - Can be run manually: python hypothesize.py
    - Can process a specific event: python hypothesize.py --event evt_20260501_001
═══════════════════════════════════════════════════════
"""

import sys
import os
import glob
import datetime
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config_loader import (
    load_config, get_workspace_path, read_yaml, write_yaml, append_to_log
)
from shared.llm_client import generate_yaml
from shared.graph_manager import GraphManager

import feedparser
import requests

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[Skill 3] yfinance not installed. Market data lookups disabled.")


# ═══════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════

HYPOTHESIS_PROMPT = """You are a financial analyst investigating the market impact of a news event on the Indian stock market (NSE/BSE).

EVENT: {event_summary}
EVENT TYPE: {event_type}
ENTITIES INVOLVED: {entities}

PRIOR KNOWLEDGE (from knowledge graph):
{graph_context}

Generate exactly 4 investigation directives to understand this event's market impact.
Each directive MUST be one of these types:

1. SECTOR_CHECK — Check how a specific Indian market sector is performing/reacting
2. COMPANY_CHECK — Check a specific NSE-listed company that might be affected
3. CORROBORATION — Search for related news to confirm the event's scope and impact
4. MACRO_CONTEXT — Check broader economic indicators (RBI policy, FII flows, index levels)

Return ONLY valid YAML:

investigations:
  - type: "SECTOR_CHECK"
    target: "the sector name to check"
    search_query: "a Google News search query for this sector"
    rationale: "why this sector might be affected"
  - type: "COMPANY_CHECK"
    target: "COMPANY_NAME"
    ticker: "TICKER.NS"
    rationale: "why this company might be affected"
  - type: "CORROBORATION"
    search_query: "a Google News search query to find related developments"
    rationale: "what we're trying to confirm"
  - type: "MACRO_CONTEXT"
    search_query: "a Google News search query for macro context"
    indicators: ["list of things to check like: nifty50, sensex, FII flows, RBI"]
    rationale: "why this macro context matters"

RULES:
- For COMPANY_CHECK, use NSE tickers (e.g., RELIANCE.NS, TCS.NS, HDFCBANK.NS)
- For SECTOR_CHECK, use Indian sectors: energy, banking, IT, pharma, auto, FMCG, metals, realty, telecom
- Search queries should be specific and recent (include "India" or "NSE" where relevant)
- Each investigation should explore a DIFFERENT angle of the event's impact
"""

SYNTHESIS_PROMPT = """You are producing a causal impact analysis for a retail investor in the Indian stock market.

EVENT: {event_summary}
EVENT TYPE: {event_type}

PRIOR KNOWLEDGE FROM GRAPH:
{graph_context}

INVESTIGATION RESULTS:
{investigation_results}

Based on ALL the evidence above, produce a structured causal chain analysis.
Return ONLY valid YAML:

causal_chain:
  trigger: "One sentence: what happened"
  mechanism: "2-3 sentences: HOW this event propagates through the Indian market. Be specific about the causal links."
  affected_sectors:
    - sector: "sector name"
      direction: "positive or negative or neutral"
      magnitude: "high or medium or low"
      reasoning: "Why this sector is affected, citing specific evidence from the investigations"
  affected_companies:
    - name: "Company Name"
      ticker: "TICKER.NS"
      direction: "positive or negative"
      reasoning: "Specific reason from evidence"
  time_horizon: "immediate or short_term or medium_term"
  confidence: "HIGH or MEDIUM or LOW"
  key_risks:
    - "Specific factor that could invalidate this analysis"
    - "Another risk factor"
  summary_for_investor: "2-3 sentence plain-English summary a retail investor can act on. No jargon."

RULES:
- Every claim in the causal chain MUST be supported by evidence from the investigations
- If investigations found conflicting signals, reflect that in confidence level
- If an investigation returned no useful data, note that as a limitation
- Be honest about uncertainty — don't overstate confidence
- Focus on Indian market impact (NSE/BSE listed companies)
"""


# ═══════════════════════════════════════════════════════════
# INVESTIGATION EXECUTORS
# ═══════════════════════════════════════════════════════════

def execute_sector_check(directive: dict) -> dict:
    """
    Execute a SECTOR_CHECK investigation.

    INPUT:
        directive — dict with keys: target (sector name), search_query, rationale

    OUTPUT:
        dict with keys: type, target, rationale, results
        results contains: news_headlines (list), market_data (dict)
    """
    target = directive.get("target", "")
    search_query = directive.get("search_query", f"India {target} sector stocks")

    results = {
        "type": "SECTOR_CHECK",
        "target": target,
        "rationale": directive.get("rationale", ""),
        "results": {
            "news_headlines": [],
            "market_data": {},
        }
    }

    # Fetch sector news via Google News RSS
    try:
        rss_url = (
            f"https://news.google.com/rss/search?"
            f"q={search_query.replace(' ', '+')}"
            f"&hl=en-IN&gl=IN&ceid=IN:en"
        )
        feed = feedparser.parse(rss_url)
        results["results"]["news_headlines"] = [
            entry.get("title", "") for entry in feed.entries[:5]
        ]
    except Exception as e:
        results["results"]["news_error"] = str(e)

    # Fetch sector ETF/index data via yfinance
    sector_tickers = {
        "banking": "^NSEBANK",
        "IT": "^CNXIT",
        "energy": "RELIANCE.NS",  # Proxy
        "pharma": "SUNPHARMA.NS",  # Proxy
        "auto": "TATAMOTORS.NS",  # Proxy
        "metals": "TATASTEEL.NS",  # Proxy
        "realty": "DLF.NS",  # Proxy
        "FMCG": "HINDUNILVR.NS",  # Proxy
        "telecom": "BHARTIARTL.NS",  # Proxy
        "infrastructure": "LT.NS",  # Proxy
    }

    if YFINANCE_AVAILABLE:
        ticker_symbol = sector_tickers.get(target.lower(), "^NSEI")  # Default to Nifty 50
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")
            if not hist.empty:
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[0]
                change_pct = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100
                results["results"]["market_data"] = {
                    "ticker_used": ticker_symbol,
                    "latest_close": round(float(latest["Close"]), 2),
                    "prev_close": round(float(prev["Close"]), 2),
                    "change_pct": round(change_pct, 2),
                    "volume": int(latest["Volume"]),
                }
        except Exception as e:
            results["results"]["market_data_error"] = str(e)

    return results


def execute_company_check(directive: dict) -> dict:
    """
    Execute a COMPANY_CHECK investigation.

    INPUT:
        directive — dict with keys: target (company name), ticker, rationale

    OUTPUT:
        dict with keys: type, target, rationale, results
        results contains: current_price, change_pct, volume, recent_news
    """
    target = directive.get("target", "")
    ticker_symbol = directive.get("ticker", "")

    results = {
        "type": "COMPANY_CHECK",
        "target": target,
        "ticker": ticker_symbol,
        "rationale": directive.get("rationale", ""),
        "results": {
            "price_data": {},
            "recent_news": [],
        }
    }

    # Fetch price data via yfinance
    if YFINANCE_AVAILABLE and ticker_symbol:
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="5d")
            if not hist.empty:
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[0]
                change_pct = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100
                results["results"]["price_data"] = {
                    "current_price": round(float(latest["Close"]), 2),
                    "prev_close": round(float(prev["Close"]), 2),
                    "change_pct": round(change_pct, 2),
                    "volume": int(latest["Volume"]),
                    "5d_high": round(float(hist["High"].max()), 2),
                    "5d_low": round(float(hist["Low"].min()), 2),
                }

            # Company info
            info = ticker.info
            results["results"]["company_info"] = {
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "market_cap": info.get("marketCap", "N/A"),
            }
        except Exception as e:
            results["results"]["price_error"] = str(e)

    # Fetch recent news about the company
    try:
        query = f"{target} India stock"
        rss_url = (
            f"https://news.google.com/rss/search?"
            f"q={query.replace(' ', '+')}"
            f"&hl=en-IN&gl=IN&ceid=IN:en"
        )
        feed = feedparser.parse(rss_url)
        results["results"]["recent_news"] = [
            entry.get("title", "") for entry in feed.entries[:3]
        ]
    except Exception as e:
        results["results"]["news_error"] = str(e)

    return results


def execute_corroboration(directive: dict) -> dict:
    """
    Execute a CORROBORATION investigation.

    INPUT:
        directive — dict with keys: search_query, rationale

    OUTPUT:
        dict with keys: type, rationale, results
        results contains: corroborating_headlines (list), source_count (int)
    """
    search_query = directive.get("search_query", "")

    results = {
        "type": "CORROBORATION",
        "rationale": directive.get("rationale", ""),
        "results": {
            "corroborating_headlines": [],
            "source_count": 0,
        }
    }

    try:
        rss_url = (
            f"https://news.google.com/rss/search?"
            f"q={search_query.replace(' ', '+')}"
            f"&hl=en-IN&gl=IN&ceid=IN:en"
        )
        feed = feedparser.parse(rss_url)
        headlines = [entry.get("title", "") for entry in feed.entries[:8]]
        results["results"]["corroborating_headlines"] = headlines
        results["results"]["source_count"] = len(headlines)
    except Exception as e:
        results["results"]["error"] = str(e)

    return results


def execute_macro_context(directive: dict) -> dict:
    """
    Execute a MACRO_CONTEXT investigation.

    INPUT:
        directive — dict with keys: search_query, indicators, rationale

    OUTPUT:
        dict with keys: type, rationale, results
        results contains: index_data (dict), macro_news (list)
    """
    results = {
        "type": "MACRO_CONTEXT",
        "rationale": directive.get("rationale", ""),
        "results": {
            "index_data": {},
            "macro_news": [],
        }
    }

    # Fetch Indian index data
    if YFINANCE_AVAILABLE:
        indices = {
            "NIFTY_50": "^NSEI",
            "SENSEX": "^BSESN",
            "NIFTY_BANK": "^NSEBANK",
            "USD_INR": "INR=X",
        }
        for name, symbol in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if not hist.empty:
                    latest = hist.iloc[-1]
                    prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[0]
                    change = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100
                    results["results"]["index_data"][name] = {
                        "value": round(float(latest["Close"]), 2),
                        "change_pct": round(change, 2),
                    }
            except Exception:
                pass

    # Fetch macro news
    search_query = directive.get("search_query", "India economy market today")
    try:
        rss_url = (
            f"https://news.google.com/rss/search?"
            f"q={search_query.replace(' ', '+')}"
            f"&hl=en-IN&gl=IN&ceid=IN:en"
        )
        feed = feedparser.parse(rss_url)
        results["results"]["macro_news"] = [
            entry.get("title", "") for entry in feed.entries[:5]
        ]
    except Exception as e:
        results["results"]["news_error"] = str(e)

    return results


# Map investigation types to their executor functions
INVESTIGATION_EXECUTORS = {
    "SECTOR_CHECK": execute_sector_check,
    "COMPANY_CHECK": execute_company_check,
    "CORROBORATION": execute_corroboration,
    "MACRO_CONTEXT": execute_macro_context,
}


# ═══════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════

def analyze_event(event: dict, graph: GraphManager, config: dict) -> dict:
    """
    Full hypothesis-driven analysis pipeline for a single event.

    INPUT:
        event  — Structured event dict from Skill 2
        graph  — GraphManager instance with prior knowledge
        config — Full config dict

    OUTPUT:
        dict — Complete analysis with causal chain, investigation results

    STEPS:
        1. Query knowledge graph for context
        2. Generate investigation hypotheses (LLM call)
        3. Execute each investigation (API calls)
        4. Synthesize causal chain (LLM call)
    """
    event_id = event.get("event_id", "unknown")
    event_summary = event.get("one_line_summary", "")
    event_type = event.get("event_type", "unknown")
    entities = event.get("entities", {})
    model = config.get("llm", {}).get("reasoning_model", "gemini-2.0-flash")

    print(f"\n  [Step 1] Querying knowledge graph...")

    # ── Step 1: Get graph context ──
    graph_context = graph.get_context_for_event(entities)
    print(f"  Graph context: {len(graph_context)} chars")

    # ── Step 2: Generate hypotheses ──
    print(f"  [Step 2] Generating investigation hypotheses...")

    entities_str = ", ".join(
        entities.get("companies", []) +
        entities.get("sectors", []) +
        entities.get("countries", []) +
        entities.get("commodities", [])
    )

    hypothesis_prompt = HYPOTHESIS_PROMPT.format(
        event_summary=event_summary,
        event_type=event_type,
        entities=entities_str,
        graph_context=graph_context,
    )

    hypotheses = generate_yaml(hypothesis_prompt, model_name=model)
    investigations_plan = hypotheses.get("investigations", [])

    if not investigations_plan:
        print(f"  ⚠ No investigations generated. Using defaults.")
        investigations_plan = [
            {"type": "CORROBORATION", "search_query": event_summary, "rationale": "Verify event"},
            {"type": "MACRO_CONTEXT", "search_query": "India market today", "indicators": ["nifty50"], "rationale": "General context"},
        ]

    print(f"  Generated {len(investigations_plan)} investigation directives")

    # ── Step 3: Execute investigations ──
    print(f"  [Step 3] Executing investigations...")
    investigation_results = []

    for i, directive in enumerate(investigations_plan[:4]):  # Max 4
        inv_type = directive.get("type", "CORROBORATION")
        executor = INVESTIGATION_EXECUTORS.get(inv_type, execute_corroboration)

        print(f"    [{i+1}] {inv_type}: {directive.get('target', directive.get('search_query', ''))[:50]}...")

        try:
            result = executor(directive)
            investigation_results.append(result)
            print(f"    ✓ Done")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            investigation_results.append({
                "type": inv_type,
                "rationale": directive.get("rationale", ""),
                "results": {"error": str(e)},
            })

        time.sleep(0.3)  # Brief pause between API calls

    # ── Step 4: Synthesize causal chain ──
    print(f"  [Step 4] Synthesizing causal chain...")

    # Format investigation results for the prompt
    inv_results_text = ""
    for i, inv in enumerate(investigation_results):
        inv_results_text += f"\n--- Investigation {i+1}: {inv.get('type', 'unknown')} ---\n"
        inv_results_text += f"Rationale: {inv.get('rationale', 'N/A')}\n"
        results = inv.get("results", {})
        for key, value in results.items():
            if isinstance(value, list):
                inv_results_text += f"{key}:\n"
                for item in value[:5]:  # Limit list items
                    inv_results_text += f"  - {str(item)[:200]}\n"
            elif isinstance(value, dict):
                inv_results_text += f"{key}:\n"
                for k, v in value.items():
                    inv_results_text += f"  {k}: {v}\n"
            else:
                inv_results_text += f"{key}: {value}\n"

    synthesis_prompt = SYNTHESIS_PROMPT.format(
        event_summary=event_summary,
        event_type=event_type,
        graph_context=graph_context,
        investigation_results=inv_results_text,
    )

    synthesis = generate_yaml(synthesis_prompt, model_name=model)
    causal_chain = synthesis.get("causal_chain", synthesis)

    # ── Build final output ──
    analysis = {
        "event_id": event_id,
        "event_summary": event_summary,
        "event_type": event_type,
        "graph_context": graph_context,
        "investigations": investigation_results,
        "causal_chain": causal_chain,
        "analyzed_at": datetime.datetime.now().isoformat(),
        "model_used": model,
    }

    return analysis


def run_hypothesis_analysis():
    """
    Main pipeline: process all unanalyzed events in data/events/.

    STEP 1: Find unprocessed events (no matching chain_ file exists)
    STEP 2: For each event, run full hypothesis-driven analysis
    STEP 3: Write causal chain to data/analysis/
    """
    print("=" * 60)
    print("[Skill 3] FinSight Hypothesis-Driven Analysis Starting...")
    print("=" * 60)

    config = load_config()
    graph = GraphManager()

    # Step 1: Find unprocessed events
    events_dir = get_workspace_path("events")
    analysis_dir = get_workspace_path("analysis")

    event_files = sorted(glob.glob(os.path.join(events_dir, "evt_*.yaml")))
    if not event_files:
        print("[Skill 3] No events to analyze.")
        append_to_log("No events to analyze.", "hypothesize.log")
        return []

    # Filter to unprocessed only
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

    # Step 2: Analyze each event
    analyses = []
    for i, event_file in enumerate(unprocessed):
        event = read_yaml(event_file)
        event_id = event.get("event_id", os.path.splitext(os.path.basename(event_file))[0])
        headline = event.get("one_line_summary", event.get("source_article", {}).get("headline", "Unknown"))

        print(f"\n{'─' * 60}")
        print(f"[Skill 3] [{i+1}/{len(unprocessed)}] Analyzing: {headline[:70]}...")

        try:
            analysis = analyze_event(event, graph, config)

            # Step 3: Write analysis
            chain_path = get_workspace_path("analysis", f"chain_{event_id}.yaml")
            write_yaml(chain_path, analysis)
            analyses.append(analysis)

            confidence = analysis.get("causal_chain", {}).get("confidence", "UNKNOWN")
            print(f"  ✓ Analysis complete. Confidence: {confidence}")
            print(f"  → Written to: chain_{event_id}.yaml")

            append_to_log(
                f"Analyzed {event_id}: {headline[:80]} | Confidence: {confidence}",
                "hypothesize.log"
            )
        except Exception as e:
            print(f"  ✗ Analysis failed: {e}")
            append_to_log(f"FAILED {event_id}: {e}", "hypothesize.log")

    print(f"\n[Skill 3] Done. Analyzed {len(analyses)}/{len(unprocessed)} events.")
    return analyses


if __name__ == "__main__":
    import argparse
    from shared.config_loader import ensure_workspace

    ensure_workspace()

    parser = argparse.ArgumentParser(description="FinSight Hypothesis-Driven Analysis")
    parser.add_argument("--event", help="Analyze a specific event ID", default=None)
    args = parser.parse_args()

    if args.event:
        # Analyze a single event
        config = load_config()
        graph = GraphManager()
        event_path = get_workspace_path("events", f"{args.event}.yaml")
        if os.path.exists(event_path):
            event = read_yaml(event_path)
            analysis = analyze_event(event, graph, config)
            chain_path = get_workspace_path("analysis", f"chain_{args.event}.yaml")
            write_yaml(chain_path, analysis)
            print(f"\nAnalysis written to: {chain_path}")
        else:
            print(f"Event not found: {event_path}")
    else:
        run_hypothesis_analysis()
