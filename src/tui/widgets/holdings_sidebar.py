"""src/tui/widgets/holdings_sidebar.py"""
from textual.containers import Vertical
from textual.widgets import ListView, ListItem, Label
from textual.reactive import reactive
from typing import Dict, Callable, Optional


class HoldingsSidebar(Vertical):
    """左侧持仓列表 — 点击切换选中股票。"""

    portfolio = reactive[Dict]({})
    selected_code = reactive("")

    DEFAULT_CSS = """
    HoldingsSidebar {
        height: auto;
        max-height: 40%;
        min-height: 6;
        border: round $primary;
        padding: 0 1;
    }
    .sidebar-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, on_select: Optional[Callable] = None, **kwargs):
        super().__init__(**kwargs)
        self._on_select = on_select

    def compose(self):
        yield Label("我的持仓", classes="sidebar-title")
        yield ListView(id="holding-list")

    def watch_portfolio(self, portfolio: Dict) -> None:
        """持仓变化时重建列表。"""
        lv = self.query_one("#holding-list", ListView)
        lv.clear()
        for code, info in portfolio.items():
            shares = info.get("shares", 0)
            cost = info.get("cost", 0)
            label = f"{code}  {shares:.0f}股 成本{cost:.2f}"
            lv.append(ListItem(Label(label), id=f"item-{code}"))
