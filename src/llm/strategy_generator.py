from openai import OpenAI
from typing import List, Dict, Any
from ..data import MaiRuiStockAPI, FinancialDataFetcher
import os

class StrategyGenerator:
    def __init__(self, api_key: str):
        """初始化 DeepSeek API"""
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.stock_api = MaiRuiStockAPI()
        self.financial_api = FinancialDataFetcher()
    
    def generate_trading_strategy(self, stock_data: Dict[str, Any], financial_data: Dict[str, Any], balance: float) -> Dict[str, Any]:
        """生成交易策略"""
        prompt = f"""请根据以下信息生成交易策略：
        股票数据：{stock_data}
        财务数据：{financial_data}
        可用资金：{balance}
        """
        
        response = self.client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": "你是一个专业的交易策略分析师，擅长制定股票交易策略。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        strategy_text = response.choices[0].message.content
        
        # 解析策略文本，提取具体操作建议
        strategy = self._parse_strategy(strategy_text)
        return strategy
    
    def _parse_strategy(self, strategy_text: str) -> Dict[str, Any]:
        """解析策略文本，提取具体操作建议"""
        strategy = {
            "action": "hold",  # buy, sell, hold
            "price": 0.0,
            "quantity": 0,
            "reason": strategy_text,
            "risk_level": "medium",  # low, medium, high
            "stop_loss": 0.0,
            "take_profit": 0.0
        }
        
        # 根据策略文本设置具体参数
        if "买入" in strategy_text:
            strategy["action"] = "buy"
        elif "卖出" in strategy_text:
            strategy["action"] = "sell"
        
        # 提取止损止盈价格
        import re
        
        # 提取止损价格
        stop_loss_match = re.search(r'止损价格[:：]\s*([\d.]+)', strategy_text)
        if stop_loss_match:
            strategy['stop_loss'] = float(stop_loss_match.group(1))
            
        # 提取止盈价格
        take_profit_match = re.search(r'止盈价格[:：]\s*([\d.]+)', strategy_text)
        if take_profit_match:
            strategy['take_profit'] = float(take_profit_match.group(1))
            
        # 提取目标价格
        target_price_match = re.search(r'目标价格[:：]\s*([\d.]+)', strategy_text)
        if target_price_match:
            strategy['price'] = float(target_price_match.group(1))
            
        # 提取交易数量
        quantity_match = re.search(r'交易数量[:：]\s*([\d.]+)', strategy_text)
        if quantity_match:
            strategy['quantity'] = int(float(quantity_match.group(1)))
            
        # 提取风险等级
        risk_match = re.search(r'风险等级[:：]\s*(低|中|高)', strategy_text)
        if risk_match:
            strategy['risk_level'] = risk_match.group(1)
            
        return strategy