# FinSight Technical Architecture & Pipeline

FinSight is designed as an autonomous, multi-agent financial intelligence system. It runs completely locally, orchestrated by a 6-step pipeline that triggers on a heartbeat (or manually via `pipeline.py`).

Here is an **extremely detailed** breakdown of how data flows through the system, step-by-step. All of these skills are now fully integrated into the `pipeline.py` orchestrator.

---

## 🟢 Skill 1: News Ingestion & Deduplication (`ingest.py`)
This is the sensory layer of the agent. It continuously monitors the world for new information.

*   **Inputs:** External APIs: Finnhub (Financial News), GDELT (Geopolitical Events), SEC EDGAR (Filings), and Google News RSS.
*   **Processing:** 
    1. Fetches raw JSON from all sources.
    2. Creates a SHA-256 hash of the article title and URL to **deduplicate** the news.
*   **Output:** Writes a queue of new, unique articles to `data/queue/pending_articles.yaml`.

---

## 🟡 Skill 2: Entity Extraction & Structuring (`extract.py`)
Converts messy, unstructured human news into machine-readable JSON/YAML.

*   **Inputs:** `data/queue/pending_articles.yaml`
*   **Processing:**
    1. Passes each raw article to an LLM to extract specific entities: `companies`, `sectors`, `countries`.
    2. Assigns an `event_type` and a `significance` score (1-10).
    3. Updates the local `knowledge_graph.json` with the new entities.
*   **Outputs:** Structured event file to `data/events/evt_<timestamp>.yaml`.

---

## 🔴 Skill 3: Impact Analysis via Historical RAG (`analyze.py`)
This is the "brain" of the operation. It uses predictive historical reasoning.

*   **Inputs:** Structured events from Skill 2, and the "Golden Dataset" stored in `ChromaDB`.
*   **Processing:**
    1. **Embedding:** Converts the new event's headline into a mathematical vector (`all-MiniLM-L6-v2`).
    2. **Metadata Filtering:** ChromaDB is queried using a hard metadata filter: `where={"event_type": event_type}`. 
    3. **Retrieval:** Pulls the top 3 closest historical analogues.
    4. **Synthesis:** LLM generates a `causal_chain` explaining how the event propagates through sectors.
*   **Outputs:** Full reasoning chain written to `data/analysis/chain_<event_id>.yaml`.

---

## 🟣 Skill 4: Portfolio Impact Mapping (`portfolio.py`)
Personalizes the global news to the user's actual money.

*   **Inputs:** The causal chain from Skill 3 and the user's local portfolio.
*   **Processing:** Fetches live prices via `yfinance`. Compares affected sectors to user holdings.
*   **Outputs:** Exposure report written to `data/analysis/impact_<event_id>.yaml`.

---

## 🟠 Skill 5: Prediction & Signal Generation (`signal_gen.py`)
Generates actionable trading signals.

*   **Inputs:** The causal chain and portfolio exposure.
*   **Processing:** LLM synthesizes a final directional signal (BULLISH/BEARISH/NEUTRAL) and time horizon.
*   **Outputs:** Trading signal written to `data/analysis/signal_<event_id>.yaml`.

---

## 🔵 Skill 6: Alert Delivery & Routing (`deliver.py`)
The user interface layer.

*   **Processing:** Routes messages to Telegram. HIGH confidence triggers an immediate alert. MEDIUM confidence is batched for a Morning Briefing.

---

## 💡 Core Concepts & Deep Dive

### 1. What does the metadata consist of? What is being embedded?
We are **not** embedding the raw news article or the massive JSON object. We take a highly compressed string: `"{headline} - {event_type}"` and embed it. The metadata attached in ChromaDB looks like this: `{"event_type": "regulatory_trade", "direction": "negative_sector"}`. This allows for hard-filtering before semantic search.

### 2. Are we only querying for the event type before retrieval?
**Yes.** This is "Structured Hybrid RAG". We pass a hard filter: `where={"event_type": "regulatory_trade"}`. This strips away 90% of the database and prevents accidentally matching a tech company's earnings beat with an antitrust lawsuit.

### 3. What exactly is a "Causal Chain"?
It is the step-by-step reasoning pathway from an event to a financial outcome. 
Example: *Trigger:* Hackers shut down Colonial Pipeline -> *Mechanism:* Gasoline supply drops causing panic buying -> *Sector Impact:* Refineries (Negative), Logistics (Negative).

### 4. The Knowledge Graph vs RAG (GraphRAG)
All entity relationships (who supplies whom, who owns whom) go into a single `knowledge_graph.json`. 
*   **How it works:** If Apple shifts production to Tata, the graph draws an edge `Apple --partners_with--> Tata`. If news breaks about a Tata factory fire, the graph retrieves "Apple" as an exposed entity.
*   **Why keep it?** RAG is terrible at "multi-hop" reasoning (e.g. Flooded Mine -> Lithium -> Batteries -> Panasonic -> Tesla). Use the Knowledge Graph for **Supply Chains** and RAG for **Historical Market Psychology**.

### 5. Local LLM Context Window
A user's portfolio YAML and a causal chain combined take under 1000 tokens. Modern local models (like `Qwen2.5-7B-Instruct-1M`) have a 1 Million token context window. The system uses less than 0.1% of its capacity, meaning it will easily handle the context without forgetting instructions.

### 6. Handling New Events
If 5 articles report on the same Fed Rate Hike, Skill 1 uses SHA-256 deduplication to combine them into **one** event, resulting in **one** causal chain. However, a rate hike and an oil spill on the same day are two distinct events and get two separate causal chains.

---

## 📄 Example: Raw News JSON to Structured Event YAML

Here is exactly what the data looks like as it enters the system, and how Skill 2 transforms it.

### Step 1: Raw API JSON (Input from Finnhub to Skill 1)
This is what a raw news feed gives us:
```json
{
  "category": "business",
  "datetime": 1714564800,
  "headline": "US Commerce Department imposes sweeping export controls on advanced AI chips to China.",
  "id": 1234567,
  "related": "NVDA, AMD",
  "source": "Reuters",
  "summary": "In a major escalation of the tech war, the US has banned the export of advanced semiconductor chips to Chinese entities, citing national security concerns. Nvidia and AMD shares fell in pre-market trading.",
  "url": "https://reuters.com/article/..."
}
```

### Step 2: Structured Event YAML (Output from Skill 2)
The LLM reads the JSON above and extracts the vital structured data, standardizing it for the RAG pipeline:
```yaml
event_id: "evt_20260502_001"
source_article:
  headline: "US Commerce Department imposes sweeping export controls on advanced AI chips to China."
  source: "Reuters"
entities:
  companies: ["NVIDIA", "AMD"]
  sectors: ["semiconductors", "technology"]
  countries: ["USA", "China"]
event_type: "regulatory_trade"
significance: 8
one_line_summary: "US bans advanced AI chip exports to China, heavily impacting Nvidia and AMD."
```
