from dataclasses import dataclass
from typing import Dict

@dataclass
class Filters:
    min_deposit_apy: float
    max_loan_apr: float
    min_spread: float
    min_term_months: int
    max_loan_term_months: int
    conservative_penalty_bp: int
    user_tax_rate_pct: float

def is_candidate(dep: Dict, loan: Dict, f: Filters) -> Dict | None:
    apy = dep["apy"]
    apr = loan["apr"]
    # учёт налога на проценты (снижаем APY)
    apy_net = apy * (1 - f.user_tax_rate_pct/100.0)
    # консервативный штраф за комиссии, условия и скрытые издержки
    penalty = f.conservative_penalty_bp / 100.0  # в процентных пунктах
    net_spread = (apy_net - apr) - penalty
    if apy >= f.min_deposit_apy and apr <= f.max_loan_apr and net_spread >= f.min_spread:
        return {
            "deposit": dep,
            "loan": loan,
            "net_spread": net_spread
        }
    return None
