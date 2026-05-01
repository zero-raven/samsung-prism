"""Skill 1 — News Ingestion: Finnhub, GDELT, SEC EDGAR, Reuters/AP RSS"""

import hashlib
import time
from dataclasses import dataclass, field

import feedparser
import httpx


@dataclass
class Article:
    title: str
    source: str
    url: str
    content: str
    timestamp: float
    hash: str = ""

    def __post_init__(self):
        self.hash = hashlib.sha256(f"{self.title}{self.url}".encode()).hexdigest()[:16]


class NewsIngestionSkill:
    def __init__(self, finnhub_api_key: str | None = None):
        self.finnhub_api_key = finnhub_api_key
        self.seen_hashes: set[str] = set()
        self.client = httpx.Client(timeout=15)

    def fetch_finnhub_news(self) -> list[Article]:
        if not self.finnhub_api_key:
            return []
        resp = self.client.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": self.finnhub_api_key},
        )
        resp.raise_for_status()
        articles = []
        for item in resp.json():
            articles.append(Article(
                title=item.get("headline", ""),
                source="finnhub",
                url=item.get("url", ""),
                content=item.get("summary", ""),
                timestamp=item.get("datetime", time.time()),
            ))
        return articles

    def fetch_gdelt_news(self) -> list[Article]:
        resp = self.client.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": "finance OR economy", "mode": "ArtList", "maxrecords": "20", "format": "json"},
        )
        resp.raise_for_status()
        articles = []
        for item in resp.json().get("articles", []):
            articles.append(Article(
                title=item.get("title", ""),
                source="gdelt",
                url=item.get("url", ""),
                content=item.get("seendate", ""),
                timestamp=time.time(),
            ))
        return articles

    def fetch_rss(self, feeds: list[str] | None = None) -> list[Article]:
        feeds = feeds or [
            "https://feeds.reuters.com/reuters/businessNews",
            "https://rsshub.app/apnews/topics/business",
        ]
        articles = []
        for feed_url in feeds:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:10]:
                    articles.append(Article(
                        title=entry.get("title", ""),
                        source="rss",
                        url=entry.get("link", ""),
                        content=entry.get("summary", ""),
                        timestamp=time.time(),
                    ))
            except Exception:
                continue
        return articles

    def deduplicate(self, articles: list[Article]) -> list[Article]:
        unique = []
        for a in articles:
            if a.hash not in self.seen_hashes:
                self.seen_hashes.add(a.hash)
                unique.append(a)
        return unique

    def ingest(self) -> list[Article]:
        all_articles = []
        for name, fn in [
            ("finnhub", self.fetch_finnhub_news),
            ("gdelt", self.fetch_gdelt_news),
            ("rss", self.fetch_rss),
        ]:
            try:
                items = fn()
                print(f"  [{name}] {len(items)} articles")
                all_articles.extend(items)
            except Exception as e:
                print(f"  [{name}] failed: {type(e).__name__}: {e}")
        return self.deduplicate(all_articles)
