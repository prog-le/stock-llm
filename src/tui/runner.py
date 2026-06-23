"""src/tui/runner.py"""
from textual.message import Message
from typing import Dict, Any, List, Optional
from src.data import MaiRuiStockAPI, FinancialDataFetcher, NewsDataFetcher
from src.llm import LLMService
from src.data.database import DatabaseManager


class AnalysisProgress(Message):
    """从 worker 线程发出到 UI 的进度事件。"""

    def __init__(self, stock_code: str, stage: str, message: str,
                 result: Optional[Dict] = None) -> None:
        super().__init__()
        self.stock_code = stock_code
        self.stage = stage       # "fetch_info" | "fetch_news" | "llm_analysis" | "stock_done" | "market_start" | "all_done"
        self.message = message
        self.result = result or {}


class AnalysisRunner:
    """后台运行器 — 在新线程里跑完整的分析流水线，发进度消息。"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def post_message(self, msg: Message) -> None:
        """由 Textual App 在初始化时替换为 self.post_message。"""
        pass

    def _emit(self, stock_code: str, stage: str, message: str,
              result: Optional[Dict] = None) -> None:
        self.post_message(AnalysisProgress(stock_code, stage, message, result))

    async def run_analysis(self, portfolio: Dict[str, Dict[str, float]],
                           balance: float) -> None:
        """在后台线程运行的完整分析流程。"""
        try:
            stock_api = MaiRuiStockAPI()
            news_api = NewsDataFetcher()
            fin_api = FinancialDataFetcher()
            llm = LLMService(self.api_key)
            db = DatabaseManager()

            # 1. 分析每只持仓股
            for stock_code, position in portfolio.items():
                self._emit(stock_code, "fetch_info", f"获取 {stock_code} 信息...")
                stock_info = stock_api.get_stock_info(stock_code)
                if not stock_info:
                    self._emit(stock_code, "error", f"无法获取 {stock_code} 信息")
                    continue

                try:
                    quote = stock_api.get_realtime_quote(stock_code)
                    stock_info["current_price"] = quote.get("price", 0)
                except Exception:
                    stock_info["current_price"] = 0

                db.save_stock_info(stock_info)

                self._emit(stock_code, "fetch_news", f"获取 {stock_code} 新闻...")
                news_list = news_api.get_stock_news(stock_code)
                db.save_news(news_list, stock_code)

                financial_data = fin_api.get_financial_data(stock_code)
                stock_info["position"] = position

                self._emit(stock_code, "llm_analysis", f"🤖 {stock_code} LLM 分析中...")
                result = llm.analyze_stock(stock_info, news_list, financial_data)
                if result["status"] == "success":
                    result["stock_name"] = stock_info.get("name", "")
                    db.save_stock_analysis(stock_code, result)

                self._emit(stock_code, "stock_done", f"✅ {stock_code} 完成", result)

            # 2. 市场分析
            self._emit("", "market_start", "获取市场新闻...")
            market_news = news_api.get_daily_news(min_count=20)
            if not market_news:
                self._emit("", "market_skip", "⚠️ 无当日市场新闻，跳过市场分析")
                self._emit("", "all_done", "✅ 持仓分析完成（无市场新闻）")
                return

            db.save_news(market_news)
            self._emit("", "market_llm", f"🤖 市场分析开始（{len(market_news)} 条新闻）...")

            market_result = llm.analyze_market(
                market_news, balance,
                progress_callback=lambda msg: self._emit("", "market_progress", msg),
            )
            if market_result["status"] == "success":
                db.save_market_analysis(market_result, balance)

            self._emit("", "all_done", "✅ 全部完成", {
                "market_result": market_result
            })

        except Exception as e:
            self._emit("", "error", f"运行出错: {str(e)}")
