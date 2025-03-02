from openai import OpenAI
from typing import List, Dict, Any
from ..data import MaiRuiStockAPI, FinancialDataFetcher
import os

class StockSelector:
    """股票选择器"""
    
    def __init__(self, api_key: str):
        """初始化 DeepSeek API"""
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.stock_api = MaiRuiStockAPI()
        self.financial_api = FinancialDataFetcher()
    
    def analyze_stock(self, stock_data: Dict[str, Any], financial_data: Dict[str, Any]) -> str:
        """分析个股数据和财务数据"""
        prompt = f"""请分析以下股票数据和财务数据，给出投资建议：
        股票数据：{stock_data}
        财务数据：{financial_data}
        """
        
        response = self.client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": "你是一个专业的股票分析师，擅长分析股票数据和财务数据。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
    
    def select_stocks(self, stock_list: List[Dict[str, Any]], count: int = 20) -> List[Dict[str, Any]]:
        """从股票列表中选择潜力股"""
        analysis_results = []
        
        for stock in stock_list:
            analysis = self.analyze_stock(stock, {})
            if "建议买入" in analysis or "推荐" in analysis:
                analysis_results.append({
                    "stock": stock,
                    "analysis": analysis
                })
            
            if len(analysis_results) >= count:
                break
        
        return analysis_results[:count]
    
    def get_stock_selection_explanation(self, stock_data: Dict[str, Any]) -> str:
        """获取选股理由"""
        prompt = f"""请解释为什么选择这支股票：
        股票数据：{stock_data}
        """
        
        response = self.client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": "你是一个专业的股票分析师，擅长解释选股理由。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content