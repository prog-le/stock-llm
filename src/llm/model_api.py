"""
LLM 服务接口 — 使用 Instructor + Pydantic v2 实现结构化输出。

本模块封装了 DeepSeek API 调用，利用 Instructor 将模型输出
自动反序列化为预定义的 Pydantic 模型，取代手写正则解析。

公开方法
--------
- analyze_stock(stock_info, news_list, financial_data)
- analyze_market(news_list, available_cash)
"""

import json
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import instructor
from instructor.core import InstructorRetryException
from openai import OpenAI

from ..data import MaiRuiStockAPI, NewsDataFetcher, FinancialDataFetcher
from .schemas import (
    AnalysisStatus,
    MarketAnalysis,
    StockAnalysis,
    StockRecommendations,
)


class LLMService:
    """大模型服务接口 — 基于 Instructor 的结构化 LLM 调用。"""

    def __init__(self, api_key: str):
        """初始化 DeepSeek API，并通过 Instructor 包装以支持结构化输出。"""
        self.client = instructor.from_openai(
            OpenAI(api_key=api_key, base_url="https://api.deepseek.com"),
            mode=instructor.Mode.TOOLS,
        )
        self.stock_api = MaiRuiStockAPI()
        self.financial_api = FinancialDataFetcher()
        self.news_api = NewsDataFetcher()

    # ──────────────────────────────────────────────
    # 公共方法
    # ──────────────────────────────────────────────

    def analyze_stock(
        self,
        stock_info: Dict[str, Any],
        news_list: List[Dict],
        financial_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """分析股票投资价值并给出结构化交易建议。

        使用 Instructor + ``StockAnalysis`` 模型将 LLM 输出自动解析为
        结构化 dict（兼容 main.py 的 legacy 格式）。

        Args:
            stock_info: 股票基本信息（含 code, name, industry, main_business）。
            news_list: 相关新闻列表，最多取前 3 条。
            financial_data: 财务数据（含 revenue, net_profit, gross_margin, roe）。

        Returns:
            dict: 包含 status / analysis / trading_advice / timestamp 的 dict。
                  失败时返回 AnalysisStatus.error_dict 格式。
        """
        try:
            prompt = self._build_analysis_prompt(stock_info, news_list, financial_data)
            result = self.client.create(
                model="deepseek-chat",
                response_model=StockAnalysis,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的股票分析师，擅长分析公司基本面、行业前景和财务数据。",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_retries=3,
                strict=True,
            )
            return result.to_legacy_dict()
        except Exception as e:
            return self._handle_error(e)

    def analyze_market(
        self, news_list: List[Dict], available_cash: float,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """分析市场机会（三步流程：推荐股票 → 获取详情 → 深度分析）。

        Args:
            news_list: 当日市场新闻列表，最多取前 10 条。
            available_cash: 可用资金（单位：元）。
            progress_callback: 可选回调，每步执行时通知 UI（参数为进度消息字符串）。

        Returns:
            dict: 包含 status / analysis / timestamp 的 dict。
                  失败时返回 AnalysisStatus.error_dict 格式。
        """
        try:
            # 第一步：根据新闻推荐股票
            if progress_callback:
                progress_callback("第 1/3 步：AI 从新闻中推荐股票...")
            recommendations = self._step1_recommend_stocks(news_list)
            recommended_stocks = [r.code for r in recommendations.recommendations]
            print(f"\n解析出的股票代码: {recommended_stocks}")

            if not recommended_stocks:
                return AnalysisStatus.error_dict(
                    "validation_error", "未能从模型响应中解析出有效的股票代码"
                )

            # 第二步：获取推荐股票的详细信息
            if progress_callback:
                progress_callback(
                    f"第 2/3 步：获取 {len(recommended_stocks)} 只推荐股的行情/财务/新闻..."
                )
            stock_details = self._step2_fetch_details(
                recommended_stocks, progress_callback
            )

            if not stock_details:
                return AnalysisStatus.error_dict(
                    "api_error", "无法获取任何推荐股票的详细信息"
                )

            # 第三步：深入分析并生成最终建议
            if progress_callback:
                progress_callback("第 3/3 步：AI 深度分析并生成交易建议...")
            market_analysis = self._step3_deep_analysis(
                available_cash, stock_details
            )
            return market_analysis.to_legacy_dict()

        except Exception as e:
            error_msg = f"分析失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return self._handle_error(e, log_traceback=False)

    # ──────────────────────────────────────────────
    # 私有方法 — 提示词构建
    # ──────────────────────────────────────────────

    def _build_analysis_prompt(
        self,
        stock_info: Dict[str, Any],
        news_list: List[Dict],
        financial_data: Dict[str, Any],
    ) -> str:
        """构建个股分析提示词。

        注意：提示词中会包含用户的**实际持仓信息**（股数、成本、浮盈浮亏），
        以便 LLM 给出结合当前仓位的交易建议，而非泛泛的买入/卖出。
        """
        code = stock_info.get("code", "—")
        name = stock_info.get("name", "—")
        industry = stock_info.get("industry", "—")
        business = stock_info.get("main_business", "—")
        price = stock_info.get("current_price", "未知")

        # ── 持仓信息（由 AnalysisRunner 在调用前注入 stock_info["position"]） ──
        position = stock_info.get("position")
        if position:
            shares = position.get("shares", 0)
            cost = position.get("cost", 0)
            cost_basis = shares * cost
            market_value = shares * price if isinstance(price, (int, float)) else 0
            profit_pct = ((price - cost) / cost * 100) if cost > 0 and isinstance(price, (int, float)) else None
            profit_amount = market_value - cost_basis
            position_block = f"""已持仓数量: {shares:.0f} 股
持仓成本价: {cost:.2f} 元/股
持仓总成本: {cost_basis:.2f} 元
当前市值: {market_value:.2f} 元"""
            if profit_pct is not None:
                position_block += f"""
浮盈浮亏: {profit_amount:+.2f} 元 ({profit_pct:+.1f}%)"""
        else:
            position_block = "（未持仓 — 作为新开仓参考）"

        prompt = f"""请分析以下股票的投资价值并给出具体的交易建议。

【重要】你必须基于用户的【实际持仓情况】给出交易建议，而非泛泛分析：
- 如果用户已持仓，根据盈亏状态选择「持有 / 加仓 / 减仓 / 卖出」
- 如果用户未持仓，选择「买入」或「持有」

可选交易方向说明（请从以下 5 个中选 1 个）：
- 买入：新开仓买入（当前未持仓时）
- 加仓：已持仓，追加买入以增加仓位
- 卖出：清仓卖出（全部卖出）
- 减仓：已持仓，部分卖出以降低风险
- 持有：维持现状不动

数量要求：
- 买入/加仓：数量 = 该笔买入的股数（不含已有持仓）
- 卖出/减仓：数量 = 该笔卖出的股数
- 持有：数量可填 0

1. 股票基本信息:
代码: {code}
名称: {name}
所属行业: {industry}
主营业务: {business}
当前价格: {price} 元

2. 你的实际持仓（请据此给出针对性建议）:
{position_block}

3. 最新相关新闻:
"""

        for i, news in enumerate(news_list[:3], 1):
            prompt += f"""
新闻{i}:
标题: {news.get('title')}
时间: {news.get('time')}
内容: {news.get('content')}
"""

        prompt += f"""
4. 主要财务指标:
营业收入: {financial_data.get('revenue')}
净利润: {financial_data.get('net_profit')}
毛利率: {financial_data.get('gross_margin')}
ROE: {financial_data.get('roe')}

请从以下几个方面进行分析并给出具体建议：

1. 公司基本面分析
2. 行业发展前景
3. 最新消息影响
4. 财务指标分析
5. 具体交易建议

你必须严格按照以下格式给出交易建议（包含所有字段且不能为空）：

交易建议：
交易方向：[买入/卖出/持有/加仓/减仓]
目标价格：[具体数字，单位：元]
交易数量：[具体数字，单位：股]
止损价格：[具体数字，单位：元]
止盈目标：[具体数字，单位：元]
持仓时间：[具体数字，单位：个交易日]
风险等级：[高/中/低]

注意：
1. 所有数值必须是具体的数字，不能使用范围或描述性语言
2. 价格必须精确到小数点后两位
3. 交易数量必须是100的整数倍
4. 持仓时间必须是具体的交易日数
5. 必须包含上述所有字段，且格式要完全一致

请先给出分析，然后在最后给出严格按照上述格式的交易建议。
"""
        return prompt

    # ──────────────────────────────────────────────
    # 私有方法 — 市场分析三步流程
    # ──────────────────────────────────────────────

    def _step1_recommend_stocks(self, news_list: List[Dict]) -> StockRecommendations:
        """第一步：根据新闻推荐 3-5 只股票。"""
        prompt = f"""请分析以下最新市场新闻,并推荐3-5只值得关注的股票：

1. 最新市场新闻：
"""
        for i, news in enumerate(news_list[:10], 1):
            prompt += f"""
新闻{i}:
标题: {news.get('title')}
时间: {news.get('time')}
内容: {news.get('content')}
"""

        prompt += """
请根据以上新闻分析当前市场环境，并推荐3-5只值得关注的股票。
对于每只推荐的股票，请提供：
1. 股票代码（格式为6位数字，如000001、600000等）
2. 推荐理由
3. 所属行业

注意：请不要假设或猜测股票的当前价格，我们会在后续分析中获取实时数据。
"""

        print("\n发送给模型的初始提示词:")
        print("-" * 50)
        print(prompt)
        print("-" * 50)

        result = self.client.create(
            model="deepseek-chat",
            response_model=StockRecommendations,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的投资顾问,请根据新闻信息推荐股票。请确保提供准确的股票代码（6位数字）。",
                },
                {"role": "user", "content": prompt},
            ],
            max_retries=3,
            strict=True,
        )

        print("\n模型初始响应:")
        print("-" * 50)
        print(result.model_dump_json(indent=2, ensure_ascii=False))
        print("-" * 50)

        return result

    def _step2_fetch_details(
        self, stock_codes: List[str],
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> List[Dict]:
        """第二步：获取推荐股票的详细信息（行情 + 财务 + 新闻 + 技术指标）。
        
        每只股票依次拉取 4 个数据接口（get_stock_info / financial / news / tech_indicators），
        通过 progress_callback 实时通知 UI，避免长时间无反馈。
        """
        stock_details = []
        total = len(stock_codes)
        for i, stock_code in enumerate(stock_codes, 1):
            msg = f"  [{i}/{total}] 获取 {stock_code} 行情+财务+新闻..."
            print(f"\n{msg}")
            if progress_callback:
                progress_callback(msg)
            details = self._get_stock_details(stock_code)
            if details:
                stock_details.append(details)
                ok_msg = f"  ✓ {stock_code} 详情获取完成"
                print(ok_msg)
                if progress_callback:
                    progress_callback(ok_msg)
            else:
                fail_msg = f"  ✗ {stock_code} 获取失败，跳过"
                print(fail_msg)
                if progress_callback:
                    progress_callback(fail_msg)
        return stock_details

    def _step3_deep_analysis(
        self, available_cash: float, stock_details: List[Dict]
    ) -> MarketAnalysis:
        """第三步：对推荐股票进行深入分析，生成 MarketAnalysis。"""
        prompt = f"""请对以下股票进行深入分析并给出具体交易建议：

可用资金：{available_cash}元

推荐股票详细信息：
{json.dumps(stock_details, ensure_ascii=False, indent=2)}

请根据以上信息，从风险收益比、市场趋势和估值水平等方面进行分析，并给出具体的投资建议。
对于每只股票，请明确说明：
1. 是否值得投资
2. 建议买入价格区间
3. 目标价格
4. 建议持仓比例
5. 止损点

请以清晰、结构化的方式呈现分析结果。
    1. 基本面分析 - 基于公司情况,行业前景等
    2. 技术面分析 - 基于提供的技术指标
    3. 市场情绪分析 - 基于相关新闻
4. 风险提示 - 明确指出投资风险
5. 具体交易建议

交易建议必须包含:
- 建议买入价格区间（基于技术分析给出合理区间，不要假设当前价格）
- 建议买入数量（考虑可用资金和风险分散）
- 止损位（明确的价格点位）
- 止盈目标（明确的价格点位）
- 建议持仓时间
- 风险等级（高/中/低）

重要提示：
1. 不要假设或猜测当前股票价格，请基于提供的技术指标进行分析
2. 给出的买入价格区间必须合理，与技术指标相符
3. 交易建议必须具体、可执行，不要使用模糊表述
4. 请考虑资金管理，不要将全部资金投入单一股票
"""

        print("\n发送给模型的最终提示词:")
        print("-" * 50)
        print(prompt)
        print("-" * 50)

        result = self.client.create(
            model="deepseek-chat",
            response_model=MarketAnalysis,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的投资顾问,请给出详细的分析和具体的交易建议。请不要假设股票的当前价格，而是基于提供的技术指标给出合理的买入区间。",
                },
                {"role": "user", "content": prompt},
            ],
            max_retries=3,
            strict=True,
        )

        print("\n模型最终响应:")
        print("-" * 50)
        print(result.model_dump_json(indent=2, ensure_ascii=False))
        print("-" * 50)

        return result

    # ──────────────────────────────────────────────
    # 私有方法 — 数据获取 & 错误处理
    # ──────────────────────────────────────────────

    def _get_stock_details(self, stock_code: str) -> Dict[str, Any]:
        """获取股票详细信息（用于市场分析第二步）。"""
        try:
            basic_info = self.stock_api.get_stock_info(stock_code)
            financial_data = self.financial_api.get_financial_data(stock_code)
            news = self.news_api.get_stock_news(stock_code, days=7)
            technical_indicators = self.stock_api.get_technical_indicators(stock_code)

            return {
                "basic_info": basic_info,
                "financial_data": financial_data,
                "news": news[:3],
                "technical_indicators": technical_indicators,
            }
        except Exception as e:
            print(f"获取股票 {stock_code} 详细信息失败: {str(e)}")
            return None

    @staticmethod
    def _handle_error(e: Exception, log_traceback: bool = True) -> Dict[str, Any]:
        """统一错误处理：区分 InstructorRetryException 和通用异常。

        Returns:
            AnalysisStatus.error_dict 格式的 dict。
        """
        error_msg = str(e)
        if log_traceback:
            error_msg = f"{error_msg}\n{traceback.format_exc()}"

        # Instructor 重试耗尽 → validation_error
        # NOTE: error_dict(error_msg, error_type) 签名: 第一个是 message, 第二个是 type
        if isinstance(e, InstructorRetryException):
            return AnalysisStatus.error_dict(
                f"Failed after 3 retries: {e}", "validation_error"
            )

        # 网络 / API 等通用异常 → api_error
        return AnalysisStatus.error_dict(error_msg, "api_error")
