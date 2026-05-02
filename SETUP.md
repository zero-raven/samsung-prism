# FinSight — Setup & Deployment Guide

## Quick Start (5 minutes)

### 1. Install Dependencies
```bash
cd finsight
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
# Required: Gemini API key (get free at https://aistudio.google.com/apikey)
export GEMINI_API_KEY="your_gemini_api_key_here"

# Optional: Finnhub API key (get free at https://finnhub.io)
export FINNHUB_API_KEY="your_finnhub_key_here"

# Optional: Custom data directory (defaults to finsight/data/)
export FINSIGHT_HOME="/path/to/data"
```

On Windows (PowerShell):
```powershell
$env:GEMINI_API_KEY = "your_gemini_api_key_here"
$env:FINNHUB_API_KEY = "your_finnhub_key_here"
```

### 3. Run the Pipeline
```bash
# Full pipeline (all 6 skills in sequence)
python pipeline.py

# Run a single skill
python pipeline.py --skill 1   # Ingest only
python pipeline.py --skill 3   # Hypothesize only (on existing events)

# Individual skill scripts
python ingest.py                # Skill 1
python extract.py               # Skill 2
python hypothesize.py           # Skill 3
python portfolio.py             # Skill 4 (also: --show, --add, --remove)
python signal.py                # Skill 5
python deliver.py               # Skill 6 (also: --graph, --status)
```

---

## Deploying to Another Machine / OpenClaw Instance

### What to Copy
```
finsight/
├── shared/                 ← Core modules (MUST copy)
├── skills/                 ← SKILL.md files for OpenClaw (copy to ~/.openclaw/workspace/skills/)
├── ingest.py              ← All 6 skill scripts
├── extract.py
├── hypothesize.py
├── portfolio.py
├── signal.py
├── deliver.py
├── pipeline.py            ← Orchestrator
├── config.yaml            ← Configuration (edit for your setup)
└── requirements.txt       ← Python dependencies
```

### Steps for Another Machine
1. Copy the entire `finsight/` directory
2. `pip install -r requirements.txt`
3. Set `GEMINI_API_KEY` environment variable
4. Edit `config.yaml` if needed (news queries, default portfolio, thresholds)
5. Run `python pipeline.py` to test
6. For OpenClaw integration: copy `skills/` subdirectories to `~/.openclaw/workspace/skills/`

### OpenClaw Integration
The SKILL.md files in `skills/` are designed for OpenClaw's skill system:
- Copy each skill folder (e.g., `finsight-ingest/`) to `~/.openclaw/workspace/skills/`
- OpenClaw reads the SKILL.md and knows when/how to invoke each skill
- The agent will run `python <path>/ingest.py` etc. as directed by SKILL.md
- No code changes needed — just update paths in SKILL.md to point to your installation

---

## File Structure & Data Flow

### Data Directory (`finsight/data/` or `$FINSIGHT_HOME`)
```
data/
├── queue/
│   ├── pending_articles.yaml    ← Skill 1 writes, Skill 2 reads + clears
│   └── seen_hashes.txt          ← Dedup tracking (persists across runs)
├── events/
│   └── evt_<id>.yaml            ← Skill 2 writes, Skill 3 reads
├── analysis/
│   ├── chain_evt_<id>.yaml      ← Skill 3 writes (causal chain)
│   ├── impact_evt_<id>.yaml     ← Skill 4 writes (portfolio impact)
│   └── signal_evt_<id>.yaml     ← Skill 5 writes (trading signal)
├── graph/
│   └── knowledge_graph.json     ← Skill 2 updates, Skill 3 queries
├── portfolio/
│   └── holdings.yaml            ← User's portfolio (Skill 4 manages)
├── briefing/
│   └── queue.yaml               ← Medium-confidence events for morning briefing
├── visualizations/
│   └── graph.html               ← Pyvis interactive graph
└── logs/
    ├── ingest.log
    ├── extract.log
    ├── hypothesize.log
    ├── signal.log
    ├── deliver.log
    ├── pipeline.log
    ├── low_significance.log
    └── delivered.txt            ← Tracks which signals have been delivered
```

---

## I/O Contract Summary

| Skill | Input | Output | LLM Calls |
|-------|-------|--------|-----------|
| **1. Ingest** | RSS feeds, GDELT API, Finnhub API | `queue/pending_articles.yaml` | 0 |
| **2. Extract** | `queue/pending_articles.yaml` | `events/evt_*.yaml` + knowledge graph | 1 per article (Gemini Flash) |
| **3. Hypothesize** | `events/evt_*.yaml` + knowledge graph | `analysis/chain_*.yaml` | 2 per event (Gemini Flash) |
| **4. Portfolio** | `analysis/chain_*.yaml` + `portfolio/holdings.yaml` | `analysis/impact_*.yaml` | 0 |
| **5. Signal** | `analysis/chain_*.yaml` + `analysis/impact_*.yaml` | `analysis/signal_*.yaml` | 1 per event (Gemini Flash) |
| **6. Deliver** | All analysis files | Formatted messages + briefing queue | 0 |

**Total LLM calls per event**: ~4 (1 extract + 2 hypothesize + 1 signal)
**Total LLM calls per heartbeat**: ~4-12 (depends on how many significant events)

---

## Configuration Reference (`config.yaml`)

| Key | Purpose | Default |
|-----|---------|---------|
| `llm.extraction_model` | Model for Skill 2 entity extraction | `gemini-2.0-flash` |
| `llm.reasoning_model` | Model for Skill 3/5 hypothesis + signal | `gemini-2.0-flash` |
| `thresholds.significance_min` | Minimum significance to trigger analysis | 5 |
| `thresholds.alert_high` | Confidence threshold for immediate alert | 8 |
| `news_sources.google_news.queries` | Search terms for Indian financial news | See config |
| `portfolio.default_holdings` | Initial portfolio if none exists | 5 NSE stocks |

---

## Portability Notes

- **No hardcoded paths**: All paths are resolved relative to the `finsight/` directory
- **No hardcoded API keys**: Everything via environment variables
- **No OS-specific code**: Works on Windows, macOS, Linux
- **No database dependencies**: All data stored as YAML/JSON files
- **No training required**: LLM does all reasoning via prompts
- **Any Gemini model works**: Change `config.yaml` to use different models
