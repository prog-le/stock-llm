"""src/tui/screens/market.py"""
from textual.containers import Vertical
from textual.widgets import Button, Static, RichLog, Input
from textual import work
from src.data import NewsDataFetcher
from src.llm import LLMService
from src.data.database import DatabaseManager


class MarketScreen(Vertical):
    TITLE = "🎯 市场扫描"

    def compose(self):
        yield Static("可用资金:", classes="section-title")
        yield Input(value="100000", placeholder="输入可用资金（元）", id="cash-input")
        yield Button("🎯 开始扫描", id="scan-btn")
        yield RichLog(id="market-log", highlight=True, max_lines=30)

    @work(thread=True)
    async def _run_scan(self) -> None:
        log = self.query_one("#market-log", RichLog)
        cash_input = self.query_one("#cash-input", Input)
        balance = float(cash_input.value or 100000)

        import os
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")
        llm = LLMService(api_key)
        news_api = NewsDataFetcher()

        # Single outer try/except — without it, a network/API failure mid-scan
        # kills the worker thread silently and the user sees a stuck button
        # with no feedback. catch-all logs the error to the RichLog so 场景 2
        # ('扫一遍市场机会') never appears to hang.
        try:
            log.write("📡 获取市场新闻...")
            news = news_api.get_daily_news(min_count=20)
            log.write(f"📰 获取到 {len(news)} 条新闻")

            log.write("🤖 第一步: LLM 推荐股票...")
            recs = llm._step1_recommend_stocks(news)
            for r in recs.recommendations:
                log.write(f"  → {r.code} {r.name}: {r.reason}")

            codes = [r.code for r in recs.recommendations]
            log.write(f"🔍 第二步: 获取 {len(codes)} 只股票详情...")
            details = llm._step2_fetch_details(codes)

            log.write("🤖 第三步: 深度分析...")
            result = llm._step3_deep_analysis(balance, details)
            log.write(f"\n✅ 分析完成")
            log.write(f"   {result.summary[:200]}")

            for pick in result.top_picks:
                log.write(
                    f"\n🏆 {pick.code}: {pick.direction} "
                    f"区间 {pick.suggested_price_range[0]}-{pick.suggested_price_range[1]} "
                    f"目标 {pick.target_price}"
                )

            log.write(f"\n⚠️ 风险提示: {result.risk_warning[:100]}...")
            log.write(f"\n💰 仓位建议: {result.allocation_strategy[:100]}...")

            # Save to DB
            db = DatabaseManager()
            db.save_market_analysis(result.to_legacy_dict(), balance)
            log.write(f"\n💾 已保存到 SQLite")
        except Exception as e:
            # Worker thread can't use self.notify safely — log to RichLog only
            log.write(f"\n❌ 扫描失败: {e}")
            log.write("   请检查 API key (.env) 和网络连接后重试")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "scan-btn":
            self._run_scan()
