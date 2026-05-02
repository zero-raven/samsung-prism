"""End-to-end demo: News Ingestion (Skill 1) -> Telegram (Skill 6).

Run: python run_skill1.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Bot

from skills.news_ingestion.skill import NewsIngestionSkill

load_dotenv(Path(__file__).parent / ".env")


async def main():
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    finnhub_key = os.environ.get("FINNHUB_API_KEY")

    print("Fetching news from Finnhub + GDELT + RSS...")
    skill = NewsIngestionSkill(finnhub_api_key=finnhub_key)
    articles = skill.ingest()
    print(f"  {len(articles)} unique articles ingested")

    if not articles:
        print("No articles found. Check API keys / network.")
        return

    by_source = {}
    for a in articles:
        by_source.setdefault(a.source, []).append(a)

    summary_lines = ["*FinSight - News Ingestion Run*", ""]
    for source, items in by_source.items():
        summary_lines.append(f"*{source.upper()}* ({len(items)} articles)")
        for a in items[:3]:
            title = a.title[:80] + ("..." if len(a.title) > 80 else "")
            summary_lines.append(f"  - {title}")
        summary_lines.append("")

    message = "\n".join(summary_lines)
    print("\nSending summary to Telegram...")
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    print("Done. Check your Telegram chat.")


if __name__ == "__main__":
    asyncio.run(main())
