"""src/tui/screens/portfolio.py — 一站式投资组合管理。

合并原持仓日报 + 持仓 + 历史 三个页面：
- 左侧：持仓列表 + 增删改表单
- 右侧：AI 分析结果（RichLog 自动换行，不截断）
- 底部：运行分析 + 历史记录查询
"""

import json
import os
import sqlite3
from typing import Dict, Optional

from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button, DataTable, Input, Label, ListView, RichLog, Static,
)
from textual import work

from src.tui.portfolio_store import PortfolioStore
from src.tui.runner import AnalysisRunner, AnalysisProgress
from src.tui.widgets.holdings_sidebar import HoldingsSidebar
from src.data.database import DatabaseManager


class PortfolioScreen(Vertical):
    """一站式投资组合管理 — 持仓管理 + AI 分析 + 历史回顾。"""

    TITLE = "📊 投资组合"

    DEFAULT_CSS = """
    PortfolioScreen {
        height: auto;
    }
    #left-panel {
        width: 38%;
        min-width: 40;
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }
    #right-panel {
        width: 62%;
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }
    .section-title {
        text-style: bold;
        margin-top: 0;
    }
    #left-panel Input {
        margin-bottom: 0;
    }
    #advice-text {
        height: 3;
        margin-top: 1;
    }
    #bottom-bar {
        height: 3;
        padding: 0 1;
    }
    #bottom-bar RichLog {
        width: 1fr;
    }
    #bottom-bar Button {
        width: 20;
    }
    #history-form {
        height: 3;
        padding: 0 1;
    }
    #history-form Input {
        width: 1fr;
    }
    #history-table {
        height: 10;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._editing_code: Optional[str] = None

    # ── UI 构建 ──────────────────────────────────────────────

    def compose(self):
        with Horizontal(id="portfolio-main"):
            # 左栏：表单（动作） + 持仓列表（上下文）
            with Vertical(id="left-panel"):
                # 表单在前 — 用户主要操作区域，始终可见
                yield Label("添加 / 编辑持仓", classes="section-title")
                yield Input(placeholder="股票代码 (如 600519)", id="code-input")
                yield Input(placeholder="数量 (股)", id="shares-input")
                yield Input(placeholder="成本价 (元/股)", id="cost-input")
                with Horizontal():
                    yield Button("添加", id="add-btn", variant="primary")
                    yield Button("修改", id="edit-btn")
                    yield Button("删除", id="del-btn", variant="error")
                # 持仓列表在后 — 上下文，可滚动查看
                yield HoldingsSidebar(id="sidebar")

            # 右栏：分析结果（RichLog 自动换行，不截断）
            with Vertical(id="right-panel"):
                yield Static(id="stock-header")
                yield RichLog(id="analysis-text", highlight=True, max_lines=200)
                yield Static(id="advice-text")

        # 底部：进度 + 操作
        with Horizontal(id="bottom-bar"):
            yield RichLog(id="progress-log", max_lines=5)
            yield Button("▶ 运行分析", id="run-btn", classes="action-btn")

        # 底部：历史记录
        yield Static("📋 历史记录", id="history-title", classes="section-title")
        with Horizontal(id="history-form"):
            yield Input(placeholder="开始 (如 2024-01-01)", id="history-start")
            yield Input(placeholder="结束 (如 2024-12-31)", id="history-end")
            yield Button("查询", id="history-query-btn")
        yield DataTable(id="history-table")

    # ── 生命周期 ─────────────────────────────────────────────

    def on_mount(self) -> None:
        self._refresh_sidebar()
        log = self.query_one("#progress-log", RichLog)
        log.write("💡 点击左侧持仓加载分析，点击 ▶ 运行分析")
        # 初始化历史表
        h_table = self.query_one("#history-table", DataTable)
        h_table.cursor_type = "row"

    def on_show(self) -> None:
        """每次切换到本 tab 时刷新持仓列表。"""
        self._refresh_sidebar()

    # ── 持仓管理 ─────────────────────────────────────────────

    def _refresh_sidebar(self) -> None:
        """刷新左侧持仓列表。"""
        store = PortfolioStore()
        sidebar = self.query_one("#sidebar", HoldingsSidebar)
        sidebar.portfolio = store.load()

    def _clear_form(self) -> None:
        self.query_one("#code-input", Input).value = ""
        self.query_one("#shares-input", Input).value = ""
        self.query_one("#cost-input", Input).value = ""
        self._editing_code = None

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """点击持仓列表 → 填充表单 + 显示已有分析。"""
        item_id = event.item.id or ""
        code = item_id.replace("item-", "")
        if not code:
            return
        store = PortfolioStore()
        portfolio = store.load()
        info = portfolio.get(code, {})
        self.query_one("#code-input", Input).value = code
        self.query_one("#shares-input", Input).value = str(info.get("shares", ""))
        self.query_one("#cost-input", Input).value = str(info.get("cost", ""))
        self._editing_code = code
        self._load_stock_analysis(code)

    def _load_stock_analysis(self, code: str) -> None:
        """从 DB 加载已有分析结果（完整内容，不截断）。"""
        try:
            db = DatabaseManager()
            conn = sqlite3.connect(db.db_path)
            row = conn.execute(
                "SELECT analysis_data FROM stock_analysis "
                "WHERE stock_code = ? ORDER BY timestamp DESC LIMIT 1",
                (code,),
            ).fetchone()
            conn.close()
            if row and row[0]:
                data = json.loads(row[0])
                self._display_analysis(data)
                return
        except Exception:
            pass
        log = self.query_one("#analysis-text", RichLog)
        log.clear()
        log.write(f"「{code}」尚无分析记录，请点击 ▶ 运行分析")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        code = self.query_one("#code-input", Input).value.strip()
        try:
            shares = float(self.query_one("#shares-input", Input).value or 0)
        except ValueError:
            shares = 0
        try:
            cost = float(self.query_one("#cost-input", Input).value or 0)
        except ValueError:
            cost = 0
        store = PortfolioStore()

        try:
            if btn_id == "add-btn":
                if not code:
                    self.notify("请输入股票代码", severity="warning")
                    return
                if shares <= 0 or cost <= 0:
                    self.notify("数量和成本价必须大于 0", severity="warning")
                    return
                store.add(code, shares, cost)
                self._refresh_sidebar()
                self._clear_form()
                self.notify(f"已添加 {code}", severity="information")

            elif btn_id == "edit-btn":
                if not code:
                    self.notify("请先选择要修改的股票", severity="warning")
                    return
                if shares <= 0 or cost <= 0:
                    self.notify("数量和成本价必须大于 0", severity="warning")
                    return
                store.update(code, shares, cost)
                self._refresh_sidebar()
                self._clear_form()
                self.notify(f"已修改 {code}", severity="information")

            elif btn_id == "del-btn":
                if not code:
                    self.notify("请先选择要删除的股票", severity="warning")
                    return
                store.remove(code)
                self._refresh_sidebar()
                self._clear_form()
                self.notify(f"已删除 {code}", severity="information")

            elif btn_id == "run-btn":
                self._run_analysis()

            elif btn_id == "history-query-btn":
                self._query_history()

        except Exception as e:
            self.notify(f"操作失败: {e}", severity="error")

    # ── 运行分析 ─────────────────────────────────────────────

    @work(thread=True)
    async def _run_analysis(self) -> None:
        runner = AnalysisRunner(api_key=self._get_api_key())
        runner.post_message = self.post_message
        store = PortfolioStore()
        portfolio = store.load()
        await runner.run_analysis(portfolio, balance=100000.0)

    def on_analysis_progress(self, msg: AnalysisProgress) -> None:
        log = self.query_one("#progress-log", RichLog)
        log.write(msg.message)
        if msg.stage == "stock_done" and msg.result:
            self._display_analysis(msg.result)
        elif msg.stage == "all_done":
            self.notify("✅ 全部分析完成，详见进度日志", severity="information")
            # 若市场分析有结果，在日志末尾追加摘要
            if msg.result and "market_result" in msg.result:
                market = msg.result["market_result"]
                summary = market.get("analysis", "")
                if summary:
                    # 截取前 300 字作为预览，完整内容可到历史记录查看
                    log.write(f"\n📊 市场分析摘要（前 300 字）：\n{summary[:300]}")

    def _display_analysis(self, result: Dict) -> None:
        """显示分析结果 — RichLog 自动换行，完整内容不截断。"""
        log = self.query_one("#analysis-text", RichLog)
        advice_static = self.query_one("#advice-text", Static)
        log.clear()

        text = result.get("analysis", "")
        if text:
            log.write(text)

        advice = result.get("trading_advice", {})
        if advice:
            advice_static.update(
                f"交易建议: {advice.get('direction', '—')} | "
                f"目标: {advice.get('target_price', '—')} | "
                f"止损: {advice.get('stop_loss', '—')} | "
                f"止盈: {advice.get('take_profit', '—')} | "
                f"数量: {advice.get('quantity', '—')} | "
                f"持仓: {advice.get('holding_period', '—')}天 | "
                f"风险: {advice.get('risk_level', '—')}"
            )

    def _get_api_key(self) -> str:
        return os.getenv("DEEPSEEK_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")

    # ── 历史查询 ─────────────────────────────────────────────

    def _query_history(self) -> None:
        """查询历史分析记录。"""
        db = DatabaseManager()
        table = self.query_one("#history-table", DataTable)
        table.clear()
        table.add_columns("时间", "类型", "股票", "建议", "状态")

        start = self.query_one("#history-start", Input).value or "2000-01-01"
        end = self.query_one("#history-end", Input).value or "2099-12-31"

        conn = sqlite3.connect(db.db_path)
        try:
            rows = conn.execute(
                """SELECT timestamp, stock_name, trading_advice, status
                 FROM stock_analysis
                 WHERE date(timestamp) BETWEEN ? AND ?
                 ORDER BY timestamp DESC LIMIT 50""",
                (start, end),
            ).fetchall()
            for ts, name, advice_json, status in rows:
                advice = json.loads(advice_json) if advice_json else {}
                direction = advice.get("direction", "—")
                status_icon = "✅" if status == "success" else "❌"
                table.add_row(
                    ts[:16] if ts else "—",
                    "持仓日报",
                    name or "—",
                    direction,
                    status_icon,
                )

            m_rows = conn.execute(
                """SELECT timestamp, analysis_data
                 FROM market_analysis
                 WHERE date(timestamp) BETWEEN ? AND ?
                 ORDER BY timestamp DESC LIMIT 20""",
                (start, end),
            ).fetchall()
            for ts, data_json in m_rows:
                data = json.loads(data_json) if data_json else {}
                summary = data.get("summary", "—")
                status_icon = "✅" if data.get("status") == "success" else "❌"
                table.add_row(
                    ts[:16] if ts else "—",
                    "市场扫描",
                    summary[:80] if summary else "—",
                    "—",
                    status_icon,
                )
        finally:
            conn.close()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """点击历史行 → 显示详情（完整内容）。"""
        log = self.query_one("#analysis-text", RichLog)
        row = event.data_table.get_row(event.row_key)
        if row:
            log.clear()
            log.write(f"选中历史记录: {row[0]} | {row[1]} | {row[2]}")
