import asyncio
import yaml
import httpx
from typing import List, Dict
from pydantic import BaseModel
from src.utils.logger import get_logger
from src.providers.deposits_org import list_deposit_offers, list_loan_offers
from src.providers.ecb_mir import latest_avg_rates
from src.notifiers.telegram_bot import TgNotifier
from src.arbitrage import Filters, is_candidate

log = get_logger("arb_bot")

class Config(BaseModel):
    countries: List[str]
    product_filters: Dict
    telegram: Dict
    scheduler: Dict
    advanced: Dict

async def gather_offers(countries: List[str]) -> Dict[str, Dict[str, List[Dict]]]:
    result = {}
    async with httpx.AsyncClient(headers={"User-Agent":"Mozilla/5.0 (arb-bot)"} ) as client:
        for c in countries:
            dep = await list_deposit_offers(client, c)
            loan = await list_loan_offers(client, c)
            result[c] = {"deposits": dep, "loans": loan}
    return result

def load_filters(cfg: Config) -> Filters:
    pf = cfg.product_filters
    adv = cfg.advanced
    return Filters(
        min_deposit_apy=pf["min_deposit_apy"],
        max_loan_apr=pf["max_loan_apr"],
        min_spread=pf["min_spread"],
        min_term_months=pf["min_term_months"],
        max_loan_term_months=pf["max_loan_term_months"],
        conservative_penalty_bp=adv.get("conservative_penalty_bp", 50),
        user_tax_rate_pct=adv.get("user_tax_rate_pct", 0),
    )

def cross_match(off: Dict[str, Dict[str, List[Dict]]], flt: Filters) -> List[Dict]:
    signals = []
    for country, buckets in off.items():
        for dep in buckets["deposits"]:
            for loan in buckets["loans"]:
                cand = is_candidate(dep, loan, flt)
                if cand:
                    signals.append(cand)
    # сортируем по величине спреда
    signals.sort(key=lambda x: x["net_spread"], reverse=True)
    return signals

async def run_once(cfg: Config):
    log.info("Fetching offers...")
    offers = await gather_offers(cfg.countries)
    flt = load_filters(cfg)
    signals = cross_match(offers, flt)

    # Fallback: средние ставки от ЕЦБ, если по странам пусто
    if cfg.advanced.get("include_ecb_mir_fallback", True) and not signals:
        try:
            rates = await latest_avg_rates()
            log.info(f"ECB fallback: {rates}")
        except Exception as e:
            log.warning(f"ECB fallback error: {e}")

    if cfg.telegram["bot_token"].startswith("PUT_"):
        # Просто печать, чтобы можно было отладить до установки токена
        log.info(f"{len(signals)} candidates. Configure Telegram to receive messages.")
        for s in signals[:5]:
            log.info(f"CAND {s['deposit']['country']}: dep {s['deposit']['apy']}% vs loan {s['loan']['apr']}% => net {s['net_spread']:.2f}pp")
    else:
        notifier = TgNotifier(cfg.telegram["bot_token"], cfg.telegram["chat_id"])
        await notifier.send_signals(signals[:20])

async def main():
    with open("config.yaml", "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = Config(**raw)
    await run_once(cfg)

if __name__ == "__main__":
    asyncio.run(main())
