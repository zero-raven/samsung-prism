<div align="center">

# 🧠 FinSight

### *An Autonomous Cross-Domain Financial Intelligence Agent*

**Samsung PRISM Hackathon · Theme: Agentic AI for Financial Decision Support**

<br>

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-22.14%2B-339933?style=for-the-badge&logo=node.js&logoColor=white)](https://nodejs.org/)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-2026.4-6E40C9?style=for-the-badge)](https://openclaw.ai)
[![Groq](https://img.shields.io/badge/Groq-Llama%203.3%2070B-F55036?style=for-the-badge)](https://groq.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-FF6B6B?style=for-the-badge)](https://www.trychroma.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)

<br>

> *From a global event → to a sector exposure → to your specific holding,*
> *with a fully auditable causal chain, in near real time.*

<br>

[**Quick Start**](#-quick-start) · [**Architecture**](#-system-architecture) · [**Skills**](#-the-six-skills) · [**Demo Output**](#-telegram-delivery) · [**Roadmap**](#-limitations-and-future-work)

</div>

---

## 📋 Abstract

**FinSight** is a six-skill autonomous agent pipeline that monitors global news, extracts financial entities, retrieves historical analogues, maps impact onto a user's equity portfolio, generates directional trading signals, and delivers explainable alerts to a Telegram chat.

The system is orchestrated by the **[OpenClaw](https://openclaw.ai)** self-hosted agent runtime, performs **retrieval-augmented reasoning** against a curated ChromaDB of historical events, and runs entirely on a **local Python interpreter** without containers, GPUs, or paid cloud services.

> The objective is to reduce the information asymmetry between institutional and retail investors by surfacing a fully explainable chain — from a global event to a sector exposure to a specific holding — in near real time.

---

## 📑 Table of Contents

<table>
<tr>
<td valign="top" width="50%">

**Foundations**
1. [Problem Statement & Motivation](#1--problem-statement-and-motivation)
2. [System Architecture](#2--system-architecture)
3. [The Six Skills](#3--the-six-skills)
4. [Technology Stack](#4--technology-stack)
5. [Data Flow & File Lifecycle](#5--data-flow-and-file-lifecycle)
6. [Project Structure](#6--project-structure)

</td>
<td valign="top" width="50%">

**Operations**

7. [Installation & Setup](#7--installation-and-setup)
8. [Configuration Reference](#8--configuration-reference)
9. [Interactive Setup Wizard](#9--the-interactive-setup-wizard)
10. [Live Progress Display](#10--live-progress-display)
11. [Telegram Delivery](#11--telegram-delivery)
12. [Rate Limiting & Token Economy](#12--rate-limiting-and-token-economy)

</td>
</tr>
<tr>
<td valign="top" width="50%">

**Runtime**

13. [OpenClaw Integration](#13--openclaw-integration)
14. [Operational Commands](#14--operational-commands)
15. [Troubleshooting](#15--troubleshooting)

</td>
<td valign="top" width="50%">

**Reference**

16. [Evaluation Alignment](#16--evaluation-alignment)
17. [Limitations & Future Work](#17--limitations-and-future-work)
18. [Authorship & License](#18--authorship-and-license)

</td>
</tr>
</table>

---

<div align="center">

## 🚀 Quick Start

</div>

```bash
git clone https://github.com/zero-raven/samsung-prism.git "OpenClaw Project"
cd "OpenClaw Project"

python -m venv venv && source venv/bin/activate     # (Windows: venv\Scripts\activate)
pip install -r requirements.txt

npm install -g openclaw@latest
openclaw onboard --non-interactive --accept-risk --auth-choice lmstudio --install-daemon

python setup.py        # ← interactive wizard handles keys, validation, and first run
```

> 💡 First run takes **3–6 minutes** (downloads sentence-transformer model, embeds the Golden Dataset).
> A Telegram alert lands in your chat as soon as the pipeline finishes.

---

## 1. 🎯 Problem Statement and Motivation

Retail investors operate at a structural disadvantage relative to institutional traders. Three failures of the current consumer landscape define the problem:

<div align="center">

| Class of tool        | What it provides            | What it omits                                          |
|:--------------------:|:---------------------------:|:------------------------------------------------------:|
| 🏛️ **Bloomberg / Reuters**  | Real-time event mapping     | Prohibitively expensive (USD 24,000+/year)             |
| 📱 **Robinhood / Zerodha**  | Price quotes, charts        | No causal reasoning from events to holdings            |
| 🤖 **Sentiment APIs**       | Aggregate sentiment scores  | No explainability; black-box scoring                   |

</div>

### The Gap

A retail investor needs, in plain language, the answer to:

> 💬 *"Event X just happened. Which of my holdings is exposed, in which direction, by how much, on what time horizon, and based on what historical analogue?"*

**FinSight produces exactly that artifact** — autonomously, on a 30-minute heartbeat, delivered as a structured Telegram message with an auditable causal chain.

---

## 2. 🏗️ System Architecture

The pipeline executes six skills sequentially. Each skill is an independent Python script with a strict YAML I/O contract; the next skill reads only the files produced by its predecessor. Skills are registered with OpenClaw (via `SKILL.md` descriptors in `~/.openclaw/workspace/skills/`) so the agent runtime can invoke them on a heartbeat schedule, but they are equally runnable from the command line via `python pipeline.py`.

```
                ┌─────────────────────────────────────────┐
                │  External sources (poll on heartbeat)   │
                │  • Google News RSS                      │
                │  • GDELT 2.0 Article List API           │
                │  • Finnhub /news endpoint               │
                └────────────────┬────────────────────────┘
                                 │
                ┌────────────────▼────────────────────────┐
                │  Skill 1 — Ingest                       │
                │    SHA-256 dedup; queue.yaml            │
                └────────────────┬────────────────────────┘
                                 │
                ┌────────────────▼────────────────────────┐
                │  Skill 2 — Extract (Groq llama-3.3-70b) │
                │    entities, sectors, significance      │
                │    knowledge_graph.json (NetworkX)      │
                └────────────────┬────────────────────────┘
                                 │
                ┌────────────────▼────────────────────────┐
                │  Skill 3 — Analyze (RAG)                │
                │    ChromaDB + sentence-transformers     │
                │    historical_events.yaml retrieval     │
                │    causal-chain synthesis (Groq)        │
                └────────────────┬────────────────────────┘
                                 │
                ┌────────────────▼────────────────────────┐
                │  Skill 4 — Portfolio                    │
                │    sector → holdings.yaml exposure %    │
                └────────────────┬────────────────────────┘
                                 │
                ┌────────────────▼────────────────────────┐
                │  Skill 5 — Signal (Groq)                │
                │    BULLISH / BEARISH / NEUTRAL          │
                │    confidence + reasoning               │
                └────────────────┬────────────────────────┘
                                 │
                ┌────────────────▼────────────────────────┐
                │  Skill 6 — Deliver                      │
                │    HIGH+exposure>5%  → Immediate alert  │
                │    MEDIUM            → Briefing queue   │
                │    LOW               → Logged only      │
                └────────────────┬────────────────────────┘
                                 │
                                 ▼
                          Telegram chat
                       (@finsight_alerts_bot)
```

> ⏱️ **Heartbeat model.** OpenClaw's gateway runs as a background service on `ws://127.0.0.1:18789` and triggers `pipeline.py` at a configurable interval (default **30 min**). Each invocation processes only the *new* articles since the last run (deduplication is persisted across invocations in `data/queue/seen_hashes.txt`).

---

## 3. 🧩 The Six Skills

<div align="center">

| # | Skill | Script | LLM Calls | Runtime |
|:-:|:------|:-------|:---------:|:-------:|
| 1️⃣ | **Ingest**    | `ingest.py`     | 0          | 60–90 s    |
| 2️⃣ | **Extract**   | `extract.py`    | 1 / article | 1.5–3 s   |
| 3️⃣ | **Analyze**   | `analyze.py`    | 2 / event  | 6–10 s     |
| 4️⃣ | **Portfolio** | `portfolio.py`  | 0          | 1–4 s      |
| 5️⃣ | **Signal**    | `signal_gen.py` | 1 / event  | 2–4 s      |
| 6️⃣ | **Deliver**   | `deliver.py`    | 0          | < 1 s      |

</div>

Each skill below documents:
- 📥 **Inputs** — files and external data consumed
- 📤 **Outputs** — files written
- 🧠 **LLM calls** — number per item processed
- ⚙️ **Algorithm** — step-by-step behaviour
- 🛡️ **Failure modes** — how the skill degrades gracefully

---

### 3.1 · Skill 1 — News Ingestion

<table>
<tr><td><b>Script</b></td><td><code>ingest.py</code></td></tr>
<tr><td><b>OpenClaw skill</b></td><td><code>finsight_news_ingestion</code></td></tr>
<tr><td><b>LLM calls</b></td><td><b>0</b></td></tr>
<tr><td><b>Typical runtime</b></td><td>60–90 seconds (network-bound)</td></tr>
</table>

**📥 Inputs**

- `config.yaml` → `news_sources.*` (per-source enable flags, query terms, max counts)
- `data/queue/seen_hashes.txt` → MD5 hashes of headlines previously seen
- Environment: `FINNHUB_API_KEY` (optional; Finnhub source skipped if blank)

**📤 Outputs**

- `data/queue/pending_articles.yaml` → list of new article dicts with fields `{id, headline, summary, source, url, published, topic}`
- `data/queue/seen_hashes.txt` → updated dedup set
- `data/logs/ingest.log` → human-readable per-run summary

**⚙️ Algorithm**

1. Load config and previously seen hashes.
2. Poll **Google News RSS** (one URL per query in `news_sources.google_news.queries`).
3. Poll **GDELT 2.0 ArtList API** (`https://api.gdeltproject.org/api/v2/doc/doc`) for each theme in `news_sources.gdelt.themes`.
4. Poll **Finnhub `/news`** for each category in `news_sources.finnhub.categories`.
5. Compute a stable hash `MD5(sorted_unique_words(lowercased(headline)))` — this collapses minor wording variants of the same story across sources.
6. Append only headlines whose hash is not in the seen set.
7. Persist the updated seen set and write the new articles to the pending queue.

**🛡️ Failure modes**

- Any source that throws on network error is logged and skipped; the run continues with the surviving sources.
- If the queue file already contains entries from a prior partial run, new articles are appended (Skill 2 will eventually drain it).

---

### 3.2 · Skill 2 — Entity Extraction

<table>
<tr><td><b>Script</b></td><td><code>extract.py</code></td></tr>
<tr><td><b>OpenClaw skill</b></td><td><code>finsight_entity_extraction</code></td></tr>
<tr><td><b>LLM calls</b></td><td><b>1 per article</b></td></tr>
<tr><td><b>Typical runtime</b></td><td>1.5–3 seconds per article + 2.5 s throttle</td></tr>
</table>

**📥 Inputs**

- `data/queue/pending_articles.yaml` (drained on success)
- `data/graph/knowledge_graph.json` (existing entity/edge state)
- `config.yaml` → `thresholds.significance_min` (default 5), `llm.extraction_model`

**📤 Outputs**

- `data/events/evt_<id>.yaml` for each article whose `significance ≥ threshold`
- `data/graph/knowledge_graph.json` (NetworkX-serialised; updated nodes/edges)
- `data/logs/extract.log`
- `data/logs/low_significance.log` (events below threshold)

**⚙️ Algorithm**

1. For each pending article, build a structured prompt asking the LLM to return YAML with the schema:

   ```yaml
   entities:
     companies: ["NTPC", "Reliance Industries"]
     sectors:   ["energy"]                 # constrained to a fixed taxonomy
     countries: ["India", "Iran"]
     commodities: ["crude oil"]
   event_type: "geopolitical"              # one of 8 fixed categories
   significance: 8                         # 1–10 integer
   one_line_summary: "Iran tensions push Brent crude up 3%, pressures airlines."
   ```

2. Parse the LLM response as YAML; on parse failure, retry once with a correction prompt that includes the parser error.
3. If `significance < threshold`, log to `low_significance.log` and skip.
4. Otherwise, write `evt_<id>.yaml` and update the knowledge graph: nodes for each entity (`type=company|sector|country|commodity|regulator`) and edges `mentioned_with` for entities co-occurring in the article.

> 🏷️ **Sector taxonomy (closed set).** The LLM is constrained to choose from:
> *energy, banking, IT, pharma, auto, FMCG, metals, realty, infrastructure, telecom, defence, media.*
> This makes downstream sector→holdings mapping deterministic.

---

### 3.3 · Skill 3 — Impact Analysis (RAG)

<table>
<tr><td><b>Script</b></td><td><code>analyze.py</code></td></tr>
<tr><td><b>OpenClaw skill</b></td><td><code>finsight_impact_analysis</code></td></tr>
<tr><td><b>LLM calls</b></td><td><b>2 per event</b> (1 retrieval rerank + 1 synthesis; retry on YAML fail)</td></tr>
<tr><td><b>Typical runtime</b></td><td>~30 s cold-start (sentence-transformer load) + 6–10 s per event</td></tr>
</table>

**📥 Inputs**

- `data/events/evt_*.yaml` (all events without a corresponding `chain_*.yaml`)
- `data/historical_events.yaml` (**"Golden Dataset"** — manually curated)
- `data/chroma_db/` (persistent ChromaDB store, auto-built on first run)
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (~90 MB, downloaded from HuggingFace Hub on first invocation, then cached locally)

**📤 Outputs**

- `data/analysis/chain_evt_<id>.yaml`
- `data/logs/analyze.log`

**⚙️ Algorithm**

1. **Index (one-time bootstrap).** On first run, parse every entry of `historical_events.yaml`, embed the description with `all-MiniLM-L6-v2`, and upsert into the ChromaDB collection `historical_events` with metadata `{event_type, sectors, year, outcome_direction}`.
2. **Retrieve.** For the new event, embed its `one_line_summary` and query the collection with a **hybrid filter**: first try exact metadata match on `event_type`; if zero hits, relax filters and re-query by similarity only.
3. **Synthesise.** Pass the current event plus the top-K analogues to the LLM under a strict YAML prompt:

   ```yaml
   causal_chain:
     trigger:    "..."                          # one sentence
     mechanism:  "..."                          # 2–3 sentences, citing analogue
     affected_sectors:
       - sector: "energy"
         direction: "positive | negative | neutral"
         magnitude: "high | medium | low"
         reasoning: "..."
     affected_companies: [...]
     time_horizon: "intraday | days | weeks | months"
     summary_for_investor: "..."                # plain-English causal chain
     key_risks: ["..."]
     confidence: "HIGH | MEDIUM | LOW"
   ```

4. Persist as `chain_evt_<id>.yaml`.

> 💡 **Why RAG instead of pure LLM?** Pure-LLM hypothesis generation hallucinated analogues *("the 2008 oil shock was caused by …")* that did not exist. The **Golden Dataset** of curated historical events forces the model to ground its mechanism explanation in real precedent, which is verifiable by the user.

---

### 3.4 · Skill 4 — Portfolio Mapping

<table>
<tr><td><b>Script</b></td><td><code>portfolio.py</code></td></tr>
<tr><td><b>OpenClaw skill</b></td><td><code>finsight_portfolio_mapping</code></td></tr>
<tr><td><b>LLM calls</b></td><td><b>0</b></td></tr>
<tr><td><b>Typical runtime</b></td><td>1–4 seconds</td></tr>
</table>

**📥 Inputs**

- `data/analysis/chain_evt_*.yaml` (any chain without a matching `impact_*.yaml`)
- `data/portfolio/holdings.yaml` (user's holdings)
- Optional: `yfinance` for live last-traded price (degrades to `avg_cost` if network or symbol fails)

**📤 Outputs**

- `data/analysis/impact_evt_<id>.yaml` per chain
- `data/logs/portfolio.log`

**⚙️ Algorithm (pure deterministic)**

1. Load holdings (each row: `{ticker, name, sector, quantity, avg_cost}`).
2. For each `affected_sector` in the chain, find all holdings whose `sector` matches.
3. Compute:
   - `total_portfolio_value = Σ (quantity × current_price)`
   - `affected_value         = Σ (quantity × current_price)` over matched rows
   - `exposure_pct           = 100 × affected_value / total_portfolio_value`
   - `direction              = positive | negative | mixed | neutral` *(positive if all affected sectors point up, mixed if signs differ)*
4. Emit `impact_evt_<id>.yaml`:

   ```yaml
   portfolio_exposure:
     total_portfolio_value: 1234567.89
     affected_value:         314141.41
     exposure_pct:                25.4
     direction: "positive"
   affected_holdings:
     - ticker: "JPM"
       name: "JPMorgan Chase & Co"
       sector: "banking"
       quantity: 75
       avg_cost: 135.20
       current_price: 142.10
       impact_direction: "positive"
       pct_of_portfolio: 25.49
   ```

---

### 3.5 · Skill 5 — Signal Generation

<table>
<tr><td><b>Script</b></td><td><code>signal_gen.py</code></td></tr>
<tr><td><b>OpenClaw skill</b></td><td><code>finsight_prediction_engine</code></td></tr>
<tr><td><b>LLM calls</b></td><td><b>1 per event</b></td></tr>
<tr><td><b>Typical runtime</b></td><td>2–4 seconds per event + 2.5 s throttle</td></tr>
</table>

**📥 Inputs**

- `data/analysis/chain_evt_<id>.yaml`
- `data/analysis/impact_evt_<id>.yaml`
- `data/graph/knowledge_graph.json` (used to surface 2nd-degree exposures — e.g. an event affecting `commodities → metals → auto`)

**📤 Outputs**

- `data/analysis/signal_evt_<id>.yaml`
- `data/logs/signal.log`

**Output schema**

```yaml
signal:
  direction:  "BULLISH | BEARISH | NEUTRAL"
  confidence: "HIGH | MEDIUM | LOW"
  horizon:    "intraday | days | weeks | months"
  reasoning:  "..."                # 2–3 sentences citing the chain + portfolio
  action_insight: "..."            # plain-English insight (NOT a buy/sell)
  risk_flags: ["..."]
event_id: "evt_20260508_091303_004"
generated_at: "2026-05-08T09:30:00"
```

> ⚠️ The prompt explicitly forbids the model from issuing buy/sell recommendations *("You do NOT give buy/sell recommendations")*. The deliverable is a **directional signal with auditable reasoning**, not investment advice.

---

### 3.6 · Skill 6 — Delivery and Routing

<table>
<tr><td><b>Script</b></td><td><code>deliver.py</code></td></tr>
<tr><td><b>OpenClaw skill</b></td><td><code>finsight_delivery</code></td></tr>
<tr><td><b>LLM calls</b></td><td><b>0</b></td></tr>
<tr><td><b>Typical runtime</b></td><td>&lt; 1 second</td></tr>
</table>

**📥 Inputs**

- `data/analysis/signal_evt_*.yaml` (every signal not present in `delivered.txt`)
- Corresponding `chain_evt_*.yaml` and `impact_evt_*.yaml`
- Environment: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

**📤 Outputs**

- Telegram message(s) sent via `https://api.telegram.org/bot<TOKEN>/sendMessage` (parse_mode `Markdown` with plain-text fallback on parse error)
- `data/briefing/queue.yaml` (queued MEDIUM-confidence events)
- `data/logs/delivered.txt` (idempotency ledger)
- `data/logs/deliver.log`

**🚦 Routing rules**

<div align="center">

| Signal confidence | Portfolio exposure | Routed to                                    |
|:-----------------:|:------------------:|:---------------------------------------------|
| 🟢 `HIGH`         | `> 5 %`            | **Immediate Telegram alert** (full causal chain) |
| 🟢 `HIGH`         | `≤ 5 %`            | Briefing queue                               |
| 🟡 `MEDIUM`       | any                | Briefing queue                               |
| ⚪ `LOW`          | any                | Logged only                                  |

</div>

The briefing queue is flushed by `python deliver.py --briefing`, which formats the top-4 events (ranked by `exposure_pct` descending) into a single *Morning Briefing* message and clears the queue. The interactive setup wizard (`setup.py`) auto-flushes the queue at the end of every successful pipeline run, so a user invoking `python setup.py` will always receive a Telegram message provided any signal was generated.

**📱 Telegram message anatomy (immediate alert)**

```
═══════════════════════════════
🔔 *FinSight Alert*
═══════════════════════════════

📰 *What happened:*
   <causal_chain.trigger>

📊 *Market Impact:*
   <causal_chain.mechanism>

🏭 *Affected Sectors:*
   ↑ banking: positive (high)
   ↓ energy:  negative (medium)

💼 *Your Portfolio Exposure:*
   Total value: ₹1,234,567.89
   Affected:    ₹314,141.41 (25.4%)
   Direction:   positive

📋 *Affected Holdings:*
   ↑ JPMorgan Chase & Co: $142.10 (25.49% of portfolio)

📈 *Signal:* BULLISH | 🔴 Confidence: HIGH | ⏱ Horizon: weeks

🔗 *Reasoning:*
   <signal.reasoning>

💡 *Insight:*  <signal.action_insight>

⚠️ *Risk Flags:*
   • <risk[0]>

═══════════════════════════════
🕐 2026-05-08 09:30 IST
_FinSight — Decision Support Only_
```

---

## 4. 🛠️ Technology Stack

<div align="center">

| Layer            | Choice                                      | Rationale                                                                         |
|:----------------:|:-------------------------------------------:|:----------------------------------------------------------------------------------|
| 🤖 **Agent runtime**    | OpenClaw 2026.4.x                           | Self-hosted, free, supports `SKILL.md` declarative skills + heartbeat scheduling  |
| 🧠 **LLM provider**     | Groq (`llama-3.3-70b-versatile`)            | Free tier (100k tokens/day), OpenAI-compatible API, sub-2-second latency          |
| 🔢 **Embeddings**       | `sentence-transformers/all-MiniLM-L6-v2`    | 384-dim, ~90 MB, runs on CPU, MIT-licensed                                        |
| 🗄️ **Vector store**    | ChromaDB 0.4+ (persistent local SQLite)     | Zero-config, no server, file-backed                                               |
| 🕸️ **Knowledge graph**  | NetworkX (JSON-serialised)                  | Pure-Python, no DB; sufficient for thousands of nodes                             |
| 💹 **Live prices**      | yfinance                                    | Free, no API key                                                                  |
| 📰 **News**             | Google News RSS, GDELT 2.0, Finnhub free    | All zero-cost; user provides only Finnhub free key                                |
| 📲 **Delivery**         | Telegram Bot API (direct REST)              | No paid SaaS, instant push, mobile-native                                         |
| 🐍 **Language**         | Python 3.11+                                | Type-hinted std-lib + pip; no compilation, no GPU                                 |

</div>

> 📝 **Note on the model alias.** `config.yaml` references `gemini-2.0-flash` for legacy reasons. The wrapper `shared/llm_client.py` resolves this to `llama-3.3-70b-versatile` on the Groq endpoint. Switching providers requires editing only the `_MODEL_MAP` dictionary in `llm_client.py`; no skill code changes.

---

## 5. 🔄 Data Flow and File Lifecycle

The pipeline writes only YAML and JSON; **no database is required**. All paths are relative to `$FINSIGHT_HOME` (defaults to `<project-root>/data/`).

```
data/
├── queue/
│   ├── pending_articles.yaml     ← Skill 1 writes; Skill 2 reads + drains
│   └── seen_hashes.txt           ← Skill 1 maintains across runs (dedup)
├── events/
│   ├── evt_<id>.yaml             ← Skill 2 writes; Skill 3 reads
│   └── _archive_pre_<date>/      ← Manual archive of stale events
├── analysis/
│   ├── chain_evt_<id>.yaml       ← Skill 3 (causal chain)
│   ├── impact_evt_<id>.yaml      ← Skill 4 (portfolio exposure)
│   └── signal_evt_<id>.yaml      ← Skill 5 (directional signal)
├── graph/
│   └── knowledge_graph.json      ← Skill 2 writes; Skills 5+ read
├── portfolio/
│   └── holdings.yaml             ← User-managed
├── briefing/
│   └── queue.yaml                ← Skill 6 writes; deliver.py --briefing drains
├── chroma_db/                    ← ChromaDB persistent store (gitignored)
│   ├── chroma.sqlite3
│   └── <uuid>/                   ← per-collection segment data
├── historical_events.yaml        ← Curated Golden Dataset
├── historical_analogues/         ← Reference dataset (legacy seed)
├── visualizations/
│   └── graph.html                ← Pyvis interactive KG snapshot
└── logs/
    ├── ingest.log
    ├── extract.log
    ├── analyze.log
    ├── portfolio.log
    ├── signal.log
    ├── deliver.log
    ├── pipeline.log
    ├── delivered.txt             ← idempotency ledger for Skill 6
    └── low_significance.log
```

> ✅ **Idempotency.** Each skill checks for the existence of its output file before processing; re-running the pipeline is safe and will only do the missing work. The `delivered.txt` ledger ensures a signal is never sent to Telegram twice.

---

## 6. 📁 Project Structure

```
OpenClaw Project/
├── README.md                ← this document
├── ARCHITECTURE.md          ← detailed architecture rationale (legacy)
├── SETUP.md                 ← legacy setup notes
├── requirements.txt         ← pinned Python dependencies
├── config.yaml              ← runtime configuration (see § 8)
├── .env.example             ← template for secret keys
├── .gitignore
│
├── pipeline.py              ← orchestrator (`python pipeline.py [--skill N]`)
├── setup.py                 ← interactive wizard (see § 9)
│
├── ingest.py                ← Skill 1
├── extract.py               ← Skill 2
├── analyze.py               ← Skill 3
├── portfolio.py             ← Skill 4
├── signal_gen.py            ← Skill 5
├── deliver.py               ← Skill 6
├── hypothesize.py           ← legacy iterative reasoning (superseded by analyze.py)
│
├── shared/
│   ├── __init__.py
│   ├── config_loader.py     ← .env + config.yaml loader; workspace helpers
│   ├── llm_client.py        ← Groq client with throttle + retry + 429 backoff
│   └── graph_manager.py     ← NetworkX wrapper, JSON (de)serialisation
│
├── skills/                  ← OpenClaw SKILL.md descriptors (one folder per skill)
│   ├── news_ingestion/
│   │   ├── SKILL.md
│   │   └── skill.py         ← legacy class wrapper, kept for OpenClaw discovery
│   ├── entity_extraction/
│   ├── impact_analysis/
│   ├── portfolio_mapping/
│   ├── prediction_engine/
│   └── delivery/
│
├── data/                    ← see § 5
└── venv/                    ← Python virtualenv (gitignored)
```

---

## 7. 📦 Installation and Setup

> 🐳 The project uses **no Docker, no containers, no cloud**. Everything runs on a local Python interpreter and a single Node.js install for OpenClaw.

### 7.1 · Prerequisites

<div align="center">

| Software   | Minimum version | Notes                                                                  |
|:----------:|:---------------:|:-----------------------------------------------------------------------|
| 🐍 **Python**  | 3.11            | 3.12 tested. 64-bit recommended.                                       |
| 🟢 **Node.js** | 22.14           | Required for OpenClaw CLI (`npm`).                                     |
| 🔧 **Git**     | any recent      | For cloning.                                                           |
| 💻 **OS**      | Win 10+ / macOS 12+ / Linux | Tested on Windows 11.                                  |
| 🧠 **RAM**     | 8 GB            | sentence-transformer model + ChromaDB embed.                           |
| 💾 **Disk**    | ~2 GB free      | venv (~1 GB) + ChromaDB + HuggingFace model cache.                     |

</div>

### 7.2 · External Account Setup *(one-time)*

Before running the wizard, obtain four credentials. Three are required, one optional.

#### 🔑 7.2.1 · Groq API key *(required)*

1. Visit <https://console.groq.com/keys>
2. Sign in with Google or GitHub
3. Click *Create API Key*. Copy the `gsk_...` value

> 💸 **Free tier:** 30 requests/min, 100,000 tokens/day on `llama-3.3-70b-versatile`.

#### 🤖 7.2.2 · Telegram bot *(required)*

1. Open Telegram, message **`@BotFather`**
2. Send `/newbot`. Choose a display name and a username ending in `_bot`
3. BotFather replies with a token of the form `8755702779:AAH...`. Copy it
4. ⚠️ **Critical:** open a chat with your new bot and send `/start`. *A bot cannot DM a user who has not initiated the conversation.*
5. To find your numeric chat ID, visit (substituting your token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   Locate `"chat":{"id": 6963299683, ...}` in the JSON. The integer is `TELEGRAM_CHAT_ID`.

#### 📊 7.2.3 · Finnhub API key *(optional)*

1. Visit <https://finnhub.io/register>
2. Sign up; copy the key from the dashboard
3. If you skip this, FinSight will still work using only Google News + GDELT

### 7.3 · Project Installation *(Windows / PowerShell)*

```powershell
# Clone
git clone https://github.com/zero-raven/samsung-prism.git "OpenClaw Project"
cd "OpenClaw Project"

# Python virtualenv
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# OpenClaw CLI (Node.js)
npm install -g openclaw@latest
openclaw onboard --non-interactive --accept-risk --auth-choice lmstudio --install-daemon

# Register the FinSight skills with OpenClaw
mkdir "$env:USERPROFILE\.openclaw\workspace\skills" -ErrorAction SilentlyContinue
xcopy /E /I /Y skills "$env:USERPROFILE\.openclaw\workspace\skills"

# Start the OpenClaw gateway (leave running in this terminal)
openclaw gateway run --port 18789
```

### 7.4 · Project Installation *(macOS / Linux)*

```bash
git clone https://github.com/zero-raven/samsung-prism.git "OpenClaw Project"
cd "OpenClaw Project"

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

npm install -g openclaw@latest
openclaw onboard --non-interactive --accept-risk --auth-choice lmstudio --install-daemon

mkdir -p ~/.openclaw/workspace/skills
cp -r skills/* ~/.openclaw/workspace/skills/

openclaw gateway run --port 18789
```

### 7.5 · Verifying the Install

In a second terminal:

```bash
openclaw gateway status            # Connectivity probe should report "ok"
openclaw skills list | grep finsight
```

You should see all six skills registered and marked `✓ ready`:

```
✓ ready  finsight_news_ingestion
✓ ready  finsight_entity_extraction
✓ ready  finsight_impact_analysis
✓ ready  finsight_portfolio_mapping
✓ ready  finsight_prediction_engine
✓ ready  finsight_delivery
```

### 7.6 · First Run

```bash
python setup.py
```

The wizard will:

1. ✅ Prompt for the Groq, Telegram bot, Finnhub keys and validate each one live against its provider's API
2. ✅ Auto-validate the chat ID against Telegram's `getChat` endpoint
3. ✅ Write all credentials to `.env`
4. ✅ Ask `Run pipeline now? [y/N]`. Type `y`
5. ✅ Stream a clean per-skill banner display while `pipeline.py` executes
6. ✅ Auto-flush the briefing queue to your Telegram chat at the end

> ⏱️ **Total wall-clock time on first run: 3–6 minutes** *(the first execution of Skill 3 downloads the sentence-transformer model, ~30 s, and embeds the historical-events seed data into ChromaDB, ~1 min)*.

---

## 8. ⚙️ Configuration Reference

### `config.yaml` — non-secret runtime configuration

| Key                                                | Type        | Default                            | Purpose                                                                       |
|:---------------------------------------------------|:-----------:|:----------------------------------:|:------------------------------------------------------------------------------|
| `llm.extraction_model`                             | string      | `gemini-2.0-flash`                 | Model alias for Skill 2; resolved by `_MODEL_MAP` in `shared/llm_client.py`   |
| `llm.reasoning_model`                              | string      | `gemini-2.0-flash`                 | Model alias for Skills 3, 5                                                   |
| `thresholds.significance_min`                      | int (1–10)  | 5                                  | Minimum extraction score to enter Skill 3                                     |
| `thresholds.alert_high`                            | int (1–10)  | 8                                  | Reserved for future immediate-alert tuning                                    |
| `news_sources.google_news.enabled`                 | bool        | true                               | Toggle Google News RSS                                                        |
| `news_sources.google_news.queries`                 | list[str]   | `["NSE India", "RBI policy"]`      | RSS query terms                                                               |
| `news_sources.google_news.region`                  | str         | `IN`                               | RSS region code                                                               |
| `news_sources.google_news.max_articles_per_query`  | int         | 3                                  | Per-query cap                                                                 |
| `news_sources.gdelt.enabled`                       | bool        | true                               | Toggle GDELT                                                                  |
| `news_sources.gdelt.themes`                        | list[str]   | `["ECON_STOCKMARKET"]`             | GDELT theme filters                                                           |
| `news_sources.gdelt.max_articles`                  | int         | 3                                  | Cap per theme                                                                 |
| `news_sources.finnhub.enabled`                     | bool        | true                               | Toggle Finnhub                                                                |
| `news_sources.finnhub.categories`                  | list[str]   | `["general"]`                      | Finnhub news categories                                                       |
| `news_sources.finnhub.max_articles`                | int         | 3                                  | Cap per category                                                              |
| `portfolio.default_holdings`                       | list[dict]  | 5 NYSE tickers                     | Used to bootstrap `data/portfolio/holdings.yaml` if absent                    |

### `.env` — secret credentials *(never committed)*

<div align="center">

| Variable             | Required | Used by                                                    |
|:---------------------|:--------:|:-----------------------------------------------------------|
| `GROQ_API_KEY`       | ✅ yes   | `shared/llm_client.py` (Skills 2, 3, 5)                    |
| `TELEGRAM_BOT_TOKEN` | ✅ yes   | `deliver.py`, `setup.py` validation                        |
| `TELEGRAM_CHAT_ID`   | ✅ yes   | `deliver.py`                                               |
| `FINNHUB_API_KEY`    | ⚪ no    | `ingest.py` (Skill 1)                                      |
| `FINSIGHT_HOME`      | ⚪ no    | Override workspace root in `shared/config_loader.py`       |

</div>

---

## 9. 🪄 The Interactive Setup Wizard

`setup.py` is the recommended entry point. It enforces a single rule: **every secret key is re-prompted on every run for safety**. The non-secret chat ID is validated against Telegram and reused if still valid.

### 9.1 · Behaviour

For each key in the order *Groq → Telegram bot → Telegram chat → Finnhub*:

1. **Secret keys** (`GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `FINNHUB_API_KEY`):
   - Prompt for the value (input hidden via `getpass` on TTY; falls back to plain `input()` when stdin is piped/redirected)
   - Live-validate against the provider's API
   - On failure, ask `Save anyway? [y/N]`; on `N`, re-prompt
   - On blank input for an *optional* key with an existing stored value, keep the existing value and label it `kept existing (not re-validated)`
2. **Non-secret keys** (`TELEGRAM_CHAT_ID`):
   - Validate the stored value first
   - Only prompt if missing or invalid
3. After all four steps, write `.env` (preserving any unrelated keys present) and prompt `Run pipeline now? [y/N]`

### 9.2 · Validators

<div align="center">

| Key                  | Endpoint                                                   | Acceptance criterion                          |
|:---------------------|:-----------------------------------------------------------|:----------------------------------------------|
| `GROQ_API_KEY`       | `GET https://api.groq.com/openai/v1/models`                | HTTP 200                                      |
| `TELEGRAM_BOT_TOKEN` | `GET https://api.telegram.org/bot<token>/getMe`            | `ok=true`, returns `username`                 |
| `TELEGRAM_CHAT_ID`   | `GET https://api.telegram.org/bot<token>/getChat`          | `ok=true`, returns chat title/username        |
| `FINNHUB_API_KEY`    | `GET https://finnhub.io/api/v1/quote?symbol=AAPL&token=…`  | `c` field is a positive number                |

</div>

> ⏱️ All validators use a `(connect=5s, read=8s)` timeout to fail fast on revoked keys or network outages.

### 9.3 · Flags

```bash
python setup.py            # standard: re-prompt secrets, then offer to run
python setup.py --keep     # opt-in: reuse stored secrets (faster, less safe)
python setup.py --no-run   # set up keys, never offer to run pipeline
```

---

## 10. 📺 Live Progress Display

When the wizard launches the pipeline, it spawns `pipeline.py` as a subprocess and parses its stdout line-by-line. Each skill is wrapped in a banner:

```
────────────────────────────────────────────────────────────
▶ SKILL 3/6: ANALYZE   (running…)
  ChromaDB retrieves historical analogues; Groq synthesizes causal chains
────────────────────────────────────────────────────────────
[Skill 3] FinSight RAG Impact Analysis Starting...
[Skill 3] Found 2 unprocessed events
   ...
   ✓ Analysis complete. Confidence: MEDIUM
[Skill 3] Done. Analyzed 2/2 events.

  ✓ SKILL 3 (ANALYZE) done in 114.6s — 2 causal chains
```

The banners use ANSI colour codes (cyan banners, green checkmarks, red errors, yellow warnings) which Windows 10+ terminals support natively. ASCII-only fallback is automatic when the terminal does not advertise ANSI.

The wrapper preserves all real-time output from each skill (per-article counts, per-event significance scores, signal directions) so the operator sees not just *that* a skill ran, but exactly *what it produced*. At the end:

```
[done] Pipeline complete in 216.5s
       Articles: 2, Events: 2, Analyses: 2, Deliveries: 2
[ok] Pipeline finished cleanly in 218.2s

────────────────────────────────────────────────────────────
▶ Flushing briefing queue → Telegram
  (sends MEDIUM-confidence events that didn't trigger immediate alerts)
────────────────────────────────────────────────────────────
  Morning briefing: 2 queued events; sending top 2 to Telegram...
  [Telegram] briefing send: OK
  ✓ Briefing delivered. Check your Telegram chat.
```

---

## 11. 📲 Telegram Delivery

### 11.1 · Architectural Choice

`deliver.py` calls the Telegram Bot API **directly** via HTTP POST rather than through the `python-telegram-bot` async wrapper. This is intentional:

- ⚡ Eliminates async/event-loop overhead in a synchronous pipeline
- 🔌 No long-running websocket connection; each message is a single REST call
- 🛡️ Markdown parse errors fall back automatically to plain text by re-posting the same body without `parse_mode`

### 11.2 · Routing Logic

Reproduced from § 3.6 for cross-reference:

```
🟢 HIGH confidence + exposure > 5%    →  Immediate alert  (full causal chain)
🟢 HIGH confidence + exposure ≤ 5%    →  Briefing queue
🟡 MEDIUM confidence (any exposure)   →  Briefing queue
⚪ LOW confidence (any exposure)      →  Logged only
```

### 11.3 · Briefing Queue Flush

Three ways to flush the briefing queue:

```bash
python setup.py                    # automatic at end of pipeline run
python deliver.py --briefing       # manual flush
python deliver.py --status         # see what's queued without flushing
```

The flush groups the top 4 queued events (sorted by `exposure_pct` descending) into a single multi-line *Morning Briefing* Telegram message and clears the queue on success.

---

## 12. 📊 Rate Limiting and Token Economy

Groq's free tier enforces two limits on `llama-3.3-70b-versatile`:

- 🚦 **30 requests per minute** (RPM)
- 🪙 **100,000 tokens per day** (TPD), reset at 00:00 UTC

`shared/llm_client.py` enforces both:

<div align="center">

| Mechanism                        | Implementation                                          |
|:---------------------------------|:--------------------------------------------------------|
| Minimum interval between calls   | `_MIN_INTERVAL_SEC = 2.5` (24 RPM, 20 % below ceiling)  |
| 429 detection                    | Match `"rate"` or `"429"` in exception message          |
| Backoff on 429                   | `max(retry_delay × 2^attempt, 20.0)` seconds            |
| Retries per call                 | 2 (so total 3 attempts)                                 |
| YAML parse retry                 | 1 corrective re-prompt with parser error injected       |

</div>

**Per-event token budget *(typical)*:**

<div align="center">

| Skill | Calls/event | Tokens/call (in + out) | Tokens/event |
|:-----:|:-----------:|:----------------------:|:------------:|
| 2     | 1           | ~1,400                 | 1,400        |
| 3     | 2           | ~2,000 each            | 4,000        |
| 5     | 1           | ~1,500                 | 1,500        |
| **Total** | **4**   |                        | **~7,000**   |

</div>

So the **100k/day TPD ceiling supports approximately 14 fresh events per day** on the free tier. `config.yaml` ships with conservative `max_articles_per_*` values to stay comfortably below this.

---

## 13. 🔌 OpenClaw Integration

OpenClaw is the agent runtime; it provides:

1. **🧩 Skill registration** — drop a `SKILL.md` (with frontmatter) into `~/.openclaw/workspace/skills/<name>/` and the runtime auto-discovers it
2. **⏱️ Heartbeat scheduling** — declarative cron-like schedule via `~/.openclaw/workspace/HEARTBEAT.md`
3. **🌐 Local gateway** — a websocket server on `127.0.0.1:18789` that hosts the skill catalogue, agent sessions, and (optional) chat-channel bridges

### 13.1 · SKILL.md format

Each skill folder under `skills/` contains a `SKILL.md` with YAML frontmatter and a freeform body that documents the skill's I/O contract:

```yaml
---
name: finsight_news_ingestion
description: "Fetches live news from external APIs and deduplicates them ..."
metadata:
  openclaw:
    requires:
      bins: ["python"]
---
# Skill 1: News Ingestion & Deduplication
## Execution Trigger
- Run `"<absolute path to venv python>" "<absolute path to ingest.py>"`.
## Input / Output Contract
- INPUT:  Live API data (Finnhub, GDELT, RSS).
- OUTPUT: data/queue/pending_articles.yaml
## Strict Rules
1. Deduplication is mandatory ...
```

The `setup.py` wizard does **not** modify these files. Re-staging the skills into OpenClaw's workspace requires:

```bash
# Windows PowerShell
xcopy /E /I /Y skills "$env:USERPROFILE\.openclaw\workspace\skills"

# macOS / Linux
cp -r skills/* ~/.openclaw/workspace/skills/
```

### 13.2 · Driving the Pipeline From OpenClaw

Two equally valid invocation models:

<div align="center">

| Model        | Trigger                                          | When to use                          |
|:------------:|:-------------------------------------------------|:-------------------------------------|
| **🎯 Direct**   | `python pipeline.py`                             | Demos, debugging, ad-hoc runs        |
| **💓 Heartbeat**| OpenClaw fires the skills on its 30-min schedule | Persistent autonomous operation      |

</div>

Both produce identical artifacts. The setup wizard uses the direct model because it is synchronous and easier to instrument with the live banner UI.

---

## 14. 💻 Operational Commands

A condensed reference of every operator-facing command:

```bash
# ─── Setup / config ──────────────────────────────────────
python setup.py                          # Interactive wizard (recommended)
python setup.py --keep                   # Skip secret re-prompt
python setup.py --no-run                 # Don't offer to run pipeline

# ─── Pipeline control ────────────────────────────────────
python pipeline.py                       # All six skills end-to-end
python pipeline.py --skill 3             # Run a single skill (1–6)

# ─── Per-skill manual runs ───────────────────────────────
python ingest.py
python extract.py
python analyze.py
python portfolio.py     [--show | --add TICKER | --remove TICKER]
python signal_gen.py
python deliver.py       [--graph | --status | --briefing]

# ─── OpenClaw runtime ────────────────────────────────────
openclaw gateway run --port 18789        # Foreground service (leave running)
openclaw gateway status                  # Connectivity probe
openclaw skills list                     # Registered skill catalogue
openclaw skills info finsight_delivery   # Read a skill's SKILL.md
openclaw doctor                          # Health checks
openclaw doctor --fix                    # Apply suggested repairs
```

---

## 15. 🩺 Troubleshooting

| Symptom                                                         | Cause                                                   | Fix                                                                                    |
|:----------------------------------------------------------------|:--------------------------------------------------------|:---------------------------------------------------------------------------------------|
| `'charmap' codec can't encode character '→'`                    | Windows console default cp1252                          | Always launch via `setup.py` (sets `PYTHONIOENCODING=utf-8`); or `chcp 65001`          |
| `getpass` prompt hangs on piped stdin                           | Windows getpass needs a TTY                             | Already handled — wizard auto-detects non-TTY and uses plain `input()`                 |
| `HTTP 429 Rate limit reached for model llama-3.3-70b`           | Daily TPD exhausted on free Groq tier                   | Wait for UTC 00:00 reset, or upgrade to Groq Dev Tier                                  |
| Telegram message never arrives                                  | All signals routed to briefing queue (none `HIGH`)      | Briefing auto-flushes via `setup.py`; or run `python deliver.py --briefing` manually   |
| Telegram returns `chat not found`                               | User never sent `/start` to the bot                     | Open Telegram, find the bot, send `/start`, retry                                      |
| `[Warning] No exact event_type match. Relaxing filters.`        | Informational only — RAG retrieval falling back         | Safe to ignore; widen `historical_events.yaml` taxonomy if frequent                    |
| ChromaDB taking >30 s on first run                              | First-time embedding of `historical_events.yaml`        | Expected; subsequent runs reuse the persistent store                                   |
| `openclaw gateway status` shows `Runtime: stopped`              | Gateway service not installed (only running foreground) | Cosmetic on Windows; foreground process is fine. To install service: `openclaw doctor --fix` |
| `[LLM] YAML parse failed (attempt 1)`                           | Model emitted invalid YAML                              | Auto-retry with corrective prompt; usually succeeds on attempt 2                       |

---

## 16. 🏆 Evaluation Alignment

FinSight maps directly to the Samsung PRISM hackathon's evaluation rubric for *Agentic AI for Financial Decision Support*:

<div align="center">

| Criterion                              | Evidence in FinSight                                                              |
|:---------------------------------------|:----------------------------------------------------------------------------------|
| ✅ Persistent autonomous agents         | OpenClaw gateway + heartbeat scheduling                                           |
| ✅ Multi-step reasoning workflow        | 6 sequential skills, each with a strict YAML I/O contract                         |
| ✅ Retrieval-augmented generation       | ChromaDB + sentence-transformers over a curated Golden Dataset                    |
| ✅ Knowledge graph                      | NetworkX, persisted as JSON, used for 2nd-degree exposure in Skill 5              |
| ✅ Proactive alerts                     | Skill 6 routes HIGH-confidence events to immediate Telegram push                  |
| ✅ Explainability                       | Every signal carries the full causal chain, historical analogue, and risk flags   |
| ✅ Real business relevance              | Targets the documented information asymmetry of Indian retail investors           |
| ✅ No paid SaaS                         | All providers are free-tier or open source                                        |
| ✅ Reproducibility                      | Single `python setup.py` from a fresh checkout reproduces the demo end-to-end     |

</div>

---

## 17. 🔭 Limitations and Future Work

### Known limitations

- 🏷️ The sector taxonomy is fixed (twelve sectors). Equities outside the taxonomy cannot be mapped automatically by Skill 4
- ⏱️ Live prices via `yfinance` may be delayed up to 15 minutes for some exchanges; FinSight is therefore a **decision support** tool, not a high-frequency trading system
- 📚 The Golden Dataset (`data/historical_events.yaml`) is hand-curated; coverage outside finance/geopolitics is sparse
- 🪙 Free Groq tier caps daily throughput at ~14 fresh events. A paid tier or self-hosted vLLM removes the cap

### 🛣️ Roadmap

- [ ] Add an SEC EDGAR ingestion source (Skill 1) for U.S. equities
- [ ] Replace the closed sector taxonomy with a dynamic embedding-based mapper
- [ ] Extend the knowledge graph with supply-chain edges sourced from filings
- [ ] Add a back-test mode that replays past `historical_events.yaml` entries against a frozen portfolio and scores Skill-5 accuracy

---
