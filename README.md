# FinSight

**An Autonomous Cross-Domain Financial Intelligence Agent**

Samsung PRISM Hackathon — Phase 1 Submission

---

## 1. Theme

**Agentic AI for Financial Decision Support.**

FinSight combines autonomous AI agents, real-time information retrieval, and explainable financial reasoning. It uses [OpenClaw](https://openclaw.ai) as the orchestration backbone to build a persistent financial intelligence assistant that monitors global events and surfaces structured impact analysis for retail investors.

---

## 2. Problem Statement

Retail investors are disadvantaged compared to institutional players because of **information asymmetry**. Institutions rapidly map global events to sector exposure and portfolio implications, while retail investors lack structured tools.

Existing solutions fail because:

- Bloomberg terminals are expensive.
- Consumer apps show prices but not causal reasoning.
- Existing sentiment tools give scores without explanations.

> Retail investors need a tool that autonomously monitors global events and produces an explainable chain from event to portfolio impact in near real time.

---

## 3. Architecture

FinSight runs as **six OpenClaw skills** on a single machine. Telegram is the user interface.

```
[ Finnhub / GDELT / SEC / RSS ]
              │
              ▼
       Skill 1: Ingest
              │
       Skill 2: Extract
              │
   Skill 3: Analyze (RAG + LLM)
              │
     Skill 4: Portfolio Map
              │
       Skill 5: Predict
              │
       Skill 6: Deliver
              │
        [ Telegram User ]
```

### 3.1 Skill 1 — News Ingestion

Pulls data from:
- **Finnhub** (financial news API)
- **GDELT** (global event database)
- **SEC EDGAR** (regulatory filings)
- **Reuters / AP RSS** feeds

Functions:
- Fetches new articles
- Deduplicates content (SHA-256 hash of title+URL)
- Tags source and timestamp
- Sends queue to next skill

### 3.2 Skill 2 — Entity Extraction

Uses a local LLM (via LM Studio) to identify:
- Companies
- Countries
- Commodities
- Regulators
- Event type
- Sector relevance

**Model:** Qwen2.5-7B-Instruct (local) — equivalent to Claude Haiku / GPT-4o-mini for extraction.

### 3.3 Skill 3 — RAG-Based Impact Analysis

Uses **ChromaDB** with curated historical analogues.

Pipeline:
1. Embed new event
2. Retrieve top-K similar historical events
3. Pass event + analogues to LLM
4. Generate explainability chain

Output schema:
```
EVENT:
ENTITIES:
HISTORICAL ANALOGUE:
SECTOR IMPACT:
CONFIDENCE:
TIME HORIZON:
REASONING:
```

**Model:** Qwen2.5-7B-Instruct-1M (local, 1M-token context) — equivalent to Claude Sonnet / GPT-4o for reasoning.

### 3.4 Skill 4 — Portfolio Mapping

Maps impacted sectors to user holdings.

**Inputs:**
- User YAML portfolio (`config/portfolio.yaml`)
- Current market data

**Outputs:**
- Portfolio exposure
- Directional risk summary

### 3.5 Skill 5 — Prediction Engine

Uses **structured LLM reasoning** (not ARIMA / LSTM).

Prompt context:
- Current event
- Historical analogues
- Price trend
- RSI
- Volume anomaly
- Macro environment

Output schema:
```
TICKER:
DIRECTION:
CONFIDENCE:
HORIZON:
BASIS:
RISK FLAGS:
```

### 3.6 Skill 6 — Delivery Layer

Handles Telegram delivery via the official Telegram Bot API.

- Immediate alerts
- Morning briefings
- On-demand queries
- Follow-up explanations

---

## 4. Tech Stack

### Platform
- **OpenClaw** — self-hosted autonomous agent runtime
- **LM Studio** — local LLM inference server

### Models
- **Qwen2.5-7B-Instruct** — entity extraction
- **Qwen2.5-7B-Instruct-1M** — reasoning, prediction (1M token context window)

### Libraries
- Python 3.12
- ChromaDB (vector store for historical analogues)
- sentence-transformers (embeddings)
- feedparser (RSS)
- httpx / requests (HTTP clients)
- PyYAML (portfolio config)
- python-telegram-bot (Telegram delivery)

---

## 5. Project Structure

```
finnhub/
├── skills/
│   ├── news_ingestion/      # Skill 1
│   ├── entity_extraction/   # Skill 2
│   ├── impact_analysis/     # Skill 3
│   ├── portfolio_mapping/   # Skill 4
│   ├── prediction_engine/   # Skill 5
│   └── delivery/            # Skill 6
├── config/
│   └── portfolio.yaml       # User holdings
├── data/
│   └── historical_analogues/ # ChromaDB seed data
├── run_skill1.py            # End-to-end demo runner
├── requirements.txt         # Python dependencies
├── .env.example             # API key template
└── README.md
```

---

## 6. Setup

### Prerequisites
- Python 3.11+
- Node.js 22.14+ (for OpenClaw)
- LM Studio (with at least one chat model loaded)

### Installation

```bash
git clone https://github.com/zero-raven/finnhub.git
cd finnhub

# Python environment
python -m venv venv
source venv/Scripts/activate    # Windows
# source venv/bin/activate      # Linux/Mac
pip install -r requirements.txt

# OpenClaw runtime
npm install -g openclaw@latest
openclaw onboard --non-interactive --accept-risk --auth-choice lmstudio --install-daemon
openclaw config set agents.defaults.model.primary "lmstudio/qwen2.5-7b-instruct-1m"
```

### Configuration

Copy `.env.example` to `.env` and fill in:

```
FINNHUB_API_KEY=<from https://finnhub.io/register>
TELEGRAM_BOT_TOKEN=<from @BotFather>
TELEGRAM_CHAT_ID=<from getUpdates API>
```

### Run

**Terminal 1 — start OpenClaw gateway:**
```bash
openclaw gateway run --port 18789
```

**Terminal 2 — start LM Studio local server**, load a model, then:
```bash
python run_skill1.py
```

---

## 7. Timeline

| Week | Focus | Deliverables |
|------|-------|-------------|
| 1 | Foundation | OpenClaw setup, Telegram bot, Skill 1 |
| 2 | Intelligence | ChromaDB, historical analogues, Skill 3 |
| 3 | Prediction | Portfolio mapping, Skill 5 |
| 4 | Polish | Alerts, demos, documentation |

---

## 8. Evaluation Alignment

FinSight demonstrates:

- ✅ **Persistent autonomous agents** (OpenClaw runtime + LM Studio)
- ✅ **Multi-step reasoning workflow** (6-skill pipeline)
- ✅ **Proactive alerts** (Telegram push on event detection)
- ✅ **Explainability** (causal chain from event → sector → portfolio)
- ✅ **Real business relevance** (retail investor information asymmetry)

---

## 9. Why This is Realistic

FinSight focuses on **explainability and decision support** rather than opaque prediction claims. The system surfaces *reasoning* (analogous historical events, causal chains) rather than just numerical forecasts — making it both technically feasible and useful to a real retail investor.

---

## License

TBD
