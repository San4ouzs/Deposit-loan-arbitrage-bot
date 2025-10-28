from typing import List, Dict
import asyncio
from telegram import Bot
from telegram.constants import ParseMode

class TgNotifier:
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    async def send_text(self, text: str):
        await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=ParseMode.HTML)

    async def send_signals(self, signals: List[Dict]):
        if not signals:
            return
        chunks = []
        for s in signals:
            chunks.append(
                f"📢 <b>Arb Candidate</b>\n"
                f"• Country: <b>{s['deposit']['country'].title()}</b>\n"
                f"• Deposit: <b>{s['deposit']['apy']:.2f}%</b> — {s['deposit']['bank']} — <a href=\"{s['deposit']['url']}\">source</a>\n"
                f"• Loan: <b>{s['loan']['apr']:.2f}%</b> — {s['loan']['bank']} ({s['loan']['loan_type']}) — <a href=\"{s['loan']['url']}\">source</a>\n"
                f"• Net spread (after penalty): <b>{s['net_spread']:.2f} pp</b>\n"
            )
        text = "\n".join(chunks)
        await self.send_text(text)
