"""Skill 6 — Delivery Layer: Telegram bot for alerts, briefings, and queries."""

import asyncio

from telegram import Bot


class DeliverySkill:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_alert(self, message: str):
        await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode="Markdown")

    async def send_impact_report(self, report: dict):
        text = (
            f"*Event:* {report.get('event', 'N/A')}\n"
            f"*Sector Impact:* {report.get('sector_impact', 'N/A')}\n"
            f"*Confidence:* {report.get('confidence', 'N/A')}\n"
            f"*Time Horizon:* {report.get('time_horizon', 'N/A')}\n"
            f"*Reasoning:* {report.get('reasoning', 'N/A')}\n"
        )
        await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode="Markdown")

    async def send_predictions(self, predictions: list[dict]):
        lines = ["*Predictions:*\n"]
        for p in predictions:
            lines.append(
                f"  {p['ticker']}: {p['direction']} "
                f"({p['confidence']}, {p['horizon']})\n"
                f"  Basis: {p['basis']}\n"
            )
        await self.bot.send_message(chat_id=self.chat_id, text="\n".join(lines), parse_mode="Markdown")

    def send_sync(self, message: str):
        asyncio.run(self.send_alert(message))
