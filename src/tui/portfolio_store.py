"""src/tui/portfolio_store.py"""
import json
from pathlib import Path
from typing import Dict, Optional

Portfolio = Dict[str, Dict[str, float]]
# e.g. {"600036": {"shares": 1000, "cost": 30.5}}


class PortfolioStore:
    """持久化持仓信息到 JSON 文件。"""

    def __init__(self, path: Path = Path("data/portfolio.json")):
        self.path = path

    def load(self) -> Portfolio:
        if not self.path.exists():
            return {}
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def save(self, portfolio: Portfolio) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)

    def add(self, code: str, shares: float, cost: float) -> Portfolio:
        data = self.load()
        data[code] = {"shares": shares, "cost": cost}
        self.save(data)
        return data

    def remove(self, code: str) -> Portfolio:
        data = self.load()
        data.pop(code, None)
        self.save(data)
        return data

    def update(self, code: str, shares: Optional[float] = None,
               cost: Optional[float] = None) -> Portfolio:
        data = self.load()
        if code in data:
            if shares is not None:
                data[code]["shares"] = shares
            if cost is not None:
                data[code]["cost"] = cost
            self.save(data)
        return data
