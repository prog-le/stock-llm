import os
import tushare as ts
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class FinancialDataFetcher:
    """财务数据获取器"""
    
    def __init__(self, token: str = None):
        """初始化财务数据获取器，从环境变量加载Tushare token
        
        Args:
            token: API token，可选，若未提供则从环境变量TUSHARE_TOKEN获取
        """
        self.token = token or os.getenv('TUSHARE_TOKEN')
        if not self.token:
            raise ValueError("请在.env文件中设置TUSHARE_TOKEN环境变量")
        
        # 初始化Tushare API
        ts.set_token(self.token)
        self.api = ts.pro_api()
    
    def get_financial_data(self, stock_code: str) -> dict:
        """获取股票财务数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            dict: 财务数据
        """
        try:
            # 调用 tushare API 获取财务数据
            df = self.api.income(
                ts_code=stock_code,
                start_date=(datetime.now().year - 1).__str__() + '0101',
                end_date=datetime.now().strftime('%Y%m%d')
            )
            
            if df.empty:
                return {}
            
            # 获取最新一期财务数据
            latest = df.iloc[0]
            return {
                'revenue': latest.get('revenue', 0),
                'net_profit': latest.get('n_income', 0),
                'gross_margin': latest.get('grossprofit_margin', 0),
                'roe': latest.get('roe', 0),
                'debt_ratio': latest.get('debt_to_assets', 0),
                'current_ratio': latest.get('current_ratio', 0),
                'inventory_turnover': latest.get('inv_turn', 0),
                'receivables_turnover': latest.get('ar_turn', 0)
            }
        except Exception as e:
            print(f"获取财务数据时出错: {str(e)}")
            return {}
    
    def get_income_statement(self, ts_code: str) -> List[Dict[str, Any]]:
        """获取利润表数据"""
        df = self.api.income(
            ts_code=ts_code,
            start_date=(datetime.now().year - 1).__str__() + '0101',
            end_date=datetime.now().strftime('%Y%m%d')
        )
        return df.to_dict('records')
    
    def get_balance_sheet(self, ts_code: str) -> List[Dict[str, Any]]:
        """获取资产负债表数据"""
        df = self.api.balancesheet(
            ts_code=ts_code,
            start_date=(datetime.now().year - 1).__str__() + '0101',
            end_date=datetime.now().strftime('%Y%m%d')
        )
        return df.to_dict('records')
    
    def get_cashflow(self, ts_code: str) -> List[Dict[str, Any]]:
        """获取现金流量表数据"""
        df = self.api.cashflow(
            ts_code=ts_code,
            start_date=(datetime.now().year - 1).__str__() + '0101',
            end_date=datetime.now().strftime('%Y%m%d')
        )
        return df.to_dict('records')
    
    def get_forecast(self, ts_code: str) -> Dict[str, Any]:
        """获取业绩预告数据"""
        df = self.api.forecast(
            ts_code=ts_code,
            start_date=(datetime.now().year).__str__() + '0101',
            end_date=datetime.now().strftime('%Y%m%d')
        )
        return df.to_dict('records')[0] if not df.empty else {}
    
    def get_express(self, ts_code: str) -> Dict[str, Any]:
        """获取业绩快报数据"""
        df = self.api.express(
            ts_code=ts_code,
            start_date=(datetime.now().year).__str__() + '0101',
            end_date=datetime.now().strftime('%Y%m%d')
        )
        return df.to_dict('records')[0] if not df.empty else {}