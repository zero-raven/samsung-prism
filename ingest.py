"""
FinSight Skill 1 — News Ingestion & Deduplication
====================================================
Fetches news from multiple sources, deduplicates, and writes to the processing queue.

═══════════════════════════════════════════════════════
INPUT:
    - config.yaml                          → News source settings
    - data/queue/seen_hashes.txt           → Previously seen article hashes

OUTPUT:
    - data/queue/pending_articles.yaml     → New articles ready for extraction
    - data/queue/seen_hashes.txt           → Updated hash list
    - data/logs/ingest.log                 → Ingestion log

TRIGGERS:
    - OpenClaw heartbeat (every 30 min)
    - Can also be run manually: python ingest.py
═══════════════════════════════════════════════════════
"""

import sys
import os
import hashlib
import datetime
import time

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config_loader import load_config, get_workspace_path, write_yaml, read_yaml, append_to_log

import feedparser
import requests


def generate_article_id() -> str:
    """Generate a unique article ID based on timestamp."""
    now = datetime.datetime.now()
    return f"art_{now.strftime('%Y%m%d_%H%M%S')}_{hash(time.time()) % 10000:04d}"


def hash_headline(headline: str) -> str:
    """Create a fuzzy hash of a headline for deduplication."""
    # Normalize: lowercase, remove punctuation, sort words
    words = sorted(set(headline.lower().split()))
    normalized = " ".join(words)
    return hashlib.md5(normalized.encode()).hexdigest()


def load_seen_hashes() -> set:
    """Load previously seen article hashes."""
    hash_file = get_workspace_path("queue", "seen_hashes.txt")
    if not os.path.exists(hash_file):
        return set()
    with open(hash_file, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_seen_hashes(hashes: set):
    """Save article hashes to file."""
    hash_file = get_workspace_path("queue", "seen_hashes.txt")
    with open(hash_file, "w") as f:
        for h in hashes:
            f.write(h + "\n")


# ── Source Fetchers ──────────────────────────────────────────────

def fetch_google_news(config: dict) -> list:
    """
    Fetch Indian financial news from Google News RSS.

    INPUT:  config.news_sources.google_news settings
    OUTPUT: list of article dicts [{headline, summary, source, url, published, topic}]
    """
    gn_config = config.get("news_sources", {}).get("google_news", {})
    if not gn_config.get("enabled", True):
        return []

    articles = []
    queries = gn_config.get("queries", ["Indian stock market"])
    region = gn_config.get("region", "IN")
    language = gn_config.get("language", "en")
    max_per_query = gn_config.get("max_articles_per_query", 10)

    for query in queries:
        url = (
            f"https://news.google.com/rss/search?"
            f"q={query.replace(' ', '+')}"
            f"&hl={language}-{region}&gl={region}&ceid={region}:{language}"
        )
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_query]:
                articles.append({
                    "id": generate_article_id(),
                    "headline": entry.get("title", ""),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "source": "google_news",
                    "url": entry.get("link", ""),
                    "published": entry.get("published", datetime.datetime.now().isoformat()),
                    "topic": _guess_topic(query),
                })
            time.sleep(0.5)  # Be polite to Google
        except Exception as e:
            append_to_log(f"Google News fetch failed for '{query}': {e}", "ingest.log")

    return articles


def fetch_gdelt(config: dict) -> list:
    """
    Fetch global events from GDELT Project API.

    INPUT:  config.news_sources.gdelt settings
    OUTPUT: list of article dicts
    """
    gdelt_config = config.get("news_sources", {}).get("gdelt", {})
    if not gdelt_config.get("enabled", True):
        return []

    articles = []
    themes = gdelt_config.get("themes", ["ECON_STOCKMARKET"])
    max_articles = gdelt_config.get("max_articles", 20)

    for theme in themes:
        url = (
            f"https://api.gdeltproject.org/api/v2/doc/doc?"
            f"query={theme}&mode=ArtList&maxrecords={max_articles}"
            f"&format=json&sort=DateDesc"
        )
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("articles", [])[:max_articles]:
                    articles.append({
                        "id": generate_article_id(),
                        "headline": item.get("title", ""),
                        "summary": item.get("seendate", "") + " - " + item.get("title", ""),
                        "source": "gdelt",
                        "url": item.get("url", ""),
                        "published": item.get("seendate", datetime.datetime.now().isoformat()),
                        "topic": _theme_to_topic(theme),
                    })
            time.sleep(0.5)
        except Exception as e:
            append_to_log(f"GDELT fetch failed for theme '{theme}': {e}", "ingest.log")

    return articles


def fetch_finnhub(config: dict) -> list:
    """
    Fetch market news from Finnhub API.

    INPUT:  config.news_sources.finnhub settings + FINNHUB_API_KEY env var
    OUTPUT: list of article dicts
    """
    fh_config = config.get("news_sources", {}).get("finnhub", {})
    if not fh_config.get("enabled", True):
        return []

    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        append_to_log("FINNHUB_API_KEY not set. Skipping Finnhub.", "ingest.log")
        return []

    articles = []
    categories = fh_config.get("categories", ["general"])
    max_articles = fh_config.get("max_articles", 15)

    for category in categories:
        url = f"https://finnhub.io/api/v1/news?category={category}&token={api_key}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for item in data[:max_articles]:
                    articles.append({
                        "id": generate_article_id(),
                        "headline": item.get("headline", ""),
                        "summary": item.get("summary", ""),
                        "source": "finnhub",
                        "url": item.get("url", ""),
                        "published": datetime.datetime.fromtimestamp(
                            item.get("datetime", 0)
                        ).isoformat(),
                        "topic": category,
                    })
            time.sleep(1)  # Respect rate limit
        except Exception as e:
            append_to_log(f"Finnhub fetch failed for '{category}': {e}", "ingest.log")

    return articles


# ── Helpers ──────────────────────────────────────────────────────

def _guess_topic(query: str) -> str:
    """Map a search query to a rough topic category."""
    query_lower = query.lower()
    if "rbi" in query_lower or "monetary" in query_lower:
        return "central_bank"
    elif "trade" in query_lower or "tariff" in query_lower:
        return "trade_policy"
    elif "oil" in query_lower or "crude" in query_lower:
        return "commodity"
    elif "banking" in query_lower:
        return "banking"
    elif "it" in query_lower or "tech" in query_lower:
        return "technology"
    return "general"


def _theme_to_topic(theme: str) -> str:
    """Map GDELT theme to topic category."""
    mapping = {
        "ECON_STOCKMARKET": "macroeconomic",
        "ECON_TRADE": "trade_policy",
        "ECON_OILPRICE": "commodity",
        "TAX_POLICY": "regulatory",
        "CENTRAL_BANK": "central_bank",
    }
    return mapping.get(theme, "geopolitical")


# ── Main Pipeline ────────────────────────────────────────────────

def run_ingestion():
    """
    Main ingestion pipeline.

    STEP 1: Load config and seen hashes
    STEP 2: Fetch articles from all sources
    STEP 3: Deduplicate against seen hashes
    STEP 4: Write new articles to pending queue
    STEP 5: Update seen hashes
    """
    print("=" * 60)
    print("[Skill 1] FinSight Ingestion Starting...")
    print("=" * 60)

    config = load_config()
    seen_hashes = load_seen_hashes()
    initial_hash_count = len(seen_hashes)

    # Step 2: Fetch from all sources
    all_articles = []

    print("[Skill 1] Fetching Google News RSS...")
    google_articles = fetch_google_news(config)
    print(f"  → {len(google_articles)} articles from Google News")
    all_articles.extend(google_articles)

    print("[Skill 1] Fetching GDELT events...")
    gdelt_articles = fetch_gdelt(config)
    print(f"  → {len(gdelt_articles)} articles from GDELT")
    all_articles.extend(gdelt_articles)

    print("[Skill 1] Fetching Finnhub news...")
    finnhub_articles = fetch_finnhub(config)
    print(f"  → {len(finnhub_articles)} articles from Finnhub")
    all_articles.extend(finnhub_articles)

    print(f"\n[Skill 1] Total fetched: {len(all_articles)}")

    # Step 3: Deduplicate
    new_articles = []
    for article in all_articles:
        h = hash_headline(article["headline"])
        if h not in seen_hashes and article["headline"].strip():
            seen_hashes.add(h)
            new_articles.append(article)

    print(f"[Skill 1] After deduplication: {len(new_articles)} new articles")

    # Step 4: Write to queue
    queue_path = get_workspace_path("queue", "pending_articles.yaml")
    existing_queue = read_yaml(queue_path)
    existing_articles = existing_queue.get("articles", [])
    existing_articles.extend(new_articles)

    write_yaml(queue_path, {
        "articles": existing_articles,
        "last_updated": datetime.datetime.now().isoformat(),
        "total_count": len(existing_articles),
    })

    # Step 5: Save hashes
    save_seen_hashes(seen_hashes)

    summary = (
        f"Ingested {len(new_articles)} new articles "
        f"(Google: {len(google_articles)}, GDELT: {len(gdelt_articles)}, "
        f"Finnhub: {len(finnhub_articles)}). "
        f"Dedup hashes: {initial_hash_count} → {len(seen_hashes)}"
    )
    append_to_log(summary, "ingest.log")
    print(f"\n[Skill 1] Done. {summary}")
    print(f"[Skill 1] Queue written to: {queue_path}")

    return new_articles


if __name__ == "__main__":
    from shared.config_loader import ensure_workspace
    ensure_workspace()
    run_ingestion()
