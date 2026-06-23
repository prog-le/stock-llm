"""src/tui/screens/realtime.py"""
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Button, Input
from src.data import MaiRuiStockAPI


class RealtimeScreen(Vertical):
    TITLE = "📈 行情"

    def compose(self):
        with Horizontal():
            yield Input(placeholder="添加股票代码", id="add-code")
            yield Button("➕", id="rt-add-btn")
            yield Button("🔄 刷新", id="refresh-btn")
            yield Button("⏱ 自动", id="auto-btn")
        yield DataTable(id="quote-table")

    def on_mount(self) -> None:
        table = self.query_one("#quote-table", DataTable)
        table.add_columns("代码", "名称", "最新价", "涨跌幅", "成交量")
        self._stock_codes = ["600036", "000858", "600519", "601318"]
        self._auto_refresh = False
        # 持有 Timer 引用：set_interval 返回的句柄需要保存，否则
        # 关闭自动刷新时无法停止，多按几次「自动」按钮会泄漏出 N 个
        # 并发计时器（每次都跑 30s 一次网络请求 → API 配额被双扣）。
        self._auto_timer = None
        self._do_refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-btn":
            self._do_refresh()
        elif event.button.id == "rt-add-btn":
            code = self.query_one("#add-code", Input).value.strip()
            if code and code not in self._stock_codes:
                self._stock_codes.append(code)
                self.query_one("#add-code", Input).value = ""
                self._do_refresh()
        elif event.button.id == "auto-btn":
            self._auto_refresh = not self._auto_refresh
            event.button.label = "⏱ 关闭" if self._auto_refresh else "⏱ 自动"
            if self._auto_refresh:
                # 已开启就不重复创建 timer（避免双开导致 N×30s 触发）
                if self._auto_timer is None:
                    self._auto_timer = self.set_interval(30, self._do_refresh)
            else:
                # 关闭时显式 stop 掉 timer，否则 30s 周期会一直跑下去
                if self._auto_timer is not None:
                    self._auto_timer.stop()
                    self._auto_timer = None

    def _do_refresh(self) -> None:
        api = MaiRuiStockAPI()
        table = self.query_one("#quote-table", DataTable)
        table.clear()
        for code in self._stock_codes:
            try:
                quote = api.get_realtime_quote(code)
                info = api.get_stock_info(code)
                price = quote.get("price", 0)
                open_p = quote.get("open", price)
                change_pct = ((price - open_p) / open_p * 100) if open_p > 0 else 0
                vol = quote.get("volume", 0)
                name = info.get("name", code) if info else code
                change_str = f"{'+' if change_pct >= 0 else ''}{change_pct:.2f}%"
                table.add_row(code, name, f"{price:.2f}", change_str, str(vol))
            except Exception:
                table.add_row(code, "—", "—", "—", "—")
