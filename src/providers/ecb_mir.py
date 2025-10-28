# ECB MIR fallback — средние ставки по депозитам и кредитам в зоне евро.
# Нужны как справка/бэкап, если по стране не получилось собрать конкретные продуктовые ставки.
# Документация: https://data.ecb.europa.eu/ (но здесь используем упрощённый CSV endpoint через SDW)
import httpx
from typing import Optional, Dict

ECB_SDW = "https://sdw.ecb.europa.eu/quickviewexport.do"

# Пример набора серий можно расширять: здесь годовые ставки по новым депозитам домохозяйств и потребкредитам
SERIES = {
    "deposit_new_business": "MIR.M.LV.B.A2A.A.R.A.2240.EUR.N",  # Латвия, пример серии (можно заменить под нужные страны)
    "loan_consumers": "MIR.M.LV.B.A2C.A.R.A.2240.EUR.N"
}

async def fetch_series(series_code: str) -> Optional[float]:
    params = {
        "trans": "1",
        "type": "csv",
        "series": series_code
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(ECB_SDW, params=params)
            r.raise_for_status()
            # Берём последнюю строку с числом
            lines = [ln for ln in r.text.splitlines() if ln and ln[0].isdigit()]
            if not lines:
                return None
            last = lines[-1].split(",")
            val = last[-1]
            return float(val)
    except Exception:
        return None

async def latest_avg_rates() -> Dict[str, Optional[float]]:
    dep = await fetch_series(SERIES["deposit_new_business"])
    loan = await fetch_series(SERIES["loan_consumers"])
    return {"ecb_deposit_avg": dep, "ecb_loan_avg": loan}
