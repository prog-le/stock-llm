"""
Pydantic v2 数据模型：定义所有 LLM 输出的结构化 schema。

本文件集中定义了 8 个模型，按功能分组：
- TradingAdvice / StockAnalysis          — 个股分析（场景 1：盘后持仓日报）
- StockRecommendation / StockRecommendations / StockDetail — 市场扫描推荐（场景 2：周末市场扫描）
- PickAdvice / MarketAnalysis            — 市场深度分析（场景 2：周末市场扫描）
- AnalysisStatus                         — 统一错误返回（场景 1/2 通用）
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ============================================================
# 个股交易建议
# ============================================================

class TradingAdvice(BaseModel):
    """单只股票的交易建议。"""

    direction: Literal["买入", "卖出", "持有", "加仓", "减仓"]
    target_price: float = Field(..., gt=0, description="目标价")
    quantity: int = Field(..., ge=0, multiple_of=100, description="数量（100 的整数倍，持有时为 0）")
    stop_loss: float = Field(..., gt=0, description="止损价")
    take_profit: float = Field(..., gt=0, description="止盈价")
    holding_period: int = Field(..., gt=0, description="持仓天数")
    risk_level: Literal["高", "中", "低"]

    @model_validator(mode="after")
    def validate_price_order(self):
        """根据交易方向校验三个价格的排序关系 + 数量约束。

        所有主动交易方向（买入/加仓/卖出/减仓）的统一逻辑：
          止损 < 目标 < 止盈（价格跌破止损就认赔，涨到止盈就锁定利润）
          数量 > 0 且为 100 整数倍
        「持有」方向无价格排序约束，数量可填 0。
        """
        if self.direction in ("买入", "加仓", "卖出", "减仓"):
            if not (self.stop_loss < self.target_price < self.take_profit):
                raise ValueError(
                    f"{self.direction}方向下，止损价 {self.stop_loss} < 目标价 {self.target_price} < "
                    f"止盈价 {self.take_profit} 不成立"
                )
            if self.quantity <= 0:
                raise ValueError(
                    f"{self.direction}方向下，quantity 必须 > 0（当前 {self.quantity}）；"
                    f"只有'持有'才允许 quantity=0"
                )
        # direction == "持有" 时：quantity 允许 0，价格无排序约束
        return self


# ============================================================
# 个股完整分析
# ============================================================

class StockAnalysis(BaseModel):
    """单只股票的完整分析结果。"""

    summary: str
    fundamental: str
    industry_outlook: str
    news_impact: str
    financial_review: str
    trading_advice: TradingAdvice
    confidence: Literal["高", "中", "低"]

    def to_legacy_dict(self) -> dict:
        """转换为主程序 main.py 期望的 dict 结构。

        保留所有 pydantic 字段（'analysis' 是 'summary' 的别名，仅为
        兼容 main.py 等历史调用方直接 print(result['analysis'])）。
        这样 db.save_stock_analysis 持久化时不会丢字段。
        """
        return {
            **self.model_dump(),
            "analysis": self.summary,  # backward-compat alias
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }


# ============================================================
# 市场扫描 - 推荐股票
# ============================================================

class StockRecommendation(BaseModel):
    """单只推荐股票的信息。"""

    code: str = Field(..., pattern=r"^\d{6}$", description="6 位数字股票代码")
    name: str = Field(..., description="股票名称")
    reason: str = Field(..., description="推荐理由")


class StockRecommendations(BaseModel):
    """市场扫描的推荐列表。"""

    recommendations: list[StockRecommendation] = Field(
        ..., min_length=3, max_length=5, description="推荐股票列表，3-5 只"
    )
    market_view: str
    key_themes: list[str]


# ============================================================
# 推荐股票详情（用于第二步 prompt 组装，非 LLM 输出）
# ============================================================

class StockDetail(BaseModel):
    """推荐股票的拉取详情打包。"""

    code: str
    name: str
    industry: str
    current_price: Optional[float] = None
    financial_summary: str
    recent_news_titles: list[str]
    technical_indicators: dict[str, float]


# ============================================================
# 市场深度分析
# ============================================================

class PickAdvice(BaseModel):
    """每只推荐股的具体持仓建议。"""

    code: str
    direction: Literal["买入", "卖出", "持有", "加仓", "减仓"]
    suggested_price_range: tuple[float, float]
    target_price: float
    suggested_position_pct: float = Field(..., description="建议仓位百分比")
    stop_loss: float
    take_profit: float
    holding_period: int
    risk_level: Literal["高", "中", "低"]
    reasoning: str


class MarketAnalysis(BaseModel):
    """市场深度分析结果。"""

    summary: str
    top_picks: list[PickAdvice]
    risk_warning: str
    allocation_strategy: str

    def to_legacy_dict(self) -> dict:
        """转换为主程序 main.py 期望的 dict 结构。

        保留所有 pydantic 字段（'analysis' 是 'summary' 的别名，仅为
        兼容 main.py 等历史调用方）。db.save_market_analysis 已使用
        json.dumps(analysis_result) 持久化整个 dict，所以 top_picks /
        risk_warning / allocation_strategy 不会被丢掉。
        """
        return {
            **self.model_dump(),
            "analysis": self.summary,  # backward-compat alias
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }


# ============================================================
# 统一错误返回
# ============================================================

class AnalysisStatus(BaseModel):
    """统一错误/成功状态返回。"""

    status: Literal["success", "error"]
    error: Optional[str] = None
    error_type: Optional[Literal["api_error", "validation_error", "max_retries_exceeded"]] = None
    timestamp: str

    @classmethod
    def error_dict(
        cls,
        error: str,
        error_type: Literal["api_error", "validation_error", "max_retries_exceeded"],
    ) -> dict:
        """创建用于返回的错误 dict。"""
        return {
            "status": "error",
            "error": error,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat(),
        }
