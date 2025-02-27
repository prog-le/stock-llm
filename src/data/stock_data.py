import requests
import json
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

class MaiRuiStockAPI:
    """麦蕊股票数据API封装"""
    
    BASE_URL = "http://api.mairui.club"
    BACKUP_URL = "http://api1.mairui.club"
    LICENSE = os.getenv('MAIRUI_LICENSE')
    

    def __init__(self):
        self.session = requests.Session()
    
    def _request(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """发送API请求
        
        Args:
            endpoint: API端点
            params: 请求参数
            
        Returns:
            List[Dict]: JSON响应数据
        """
        url = f"{self.BASE_URL}/{endpoint}/{self.LICENSE}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            # 主接口失败时尝试备用接口
            backup_url = f"{self.BACKUP_URL}/{endpoint}/{self.LICENSE}"
            response = self.session.get(backup_url, params=params)
            response.raise_for_status()
            return response.json()

    def get_stock_list(self) -> List[Dict]:
        """获取沪深两市股票列表
        
        Returns:
            List[Dict]: 包含股票代码、名称、交易所的列表
        """
        return self._request("hslt/list")

    def get_realtime_quote(self, stock_code: str) -> Dict:
        """获取股票实时行情
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Dict: 实时行情数据
        """
        try:
            data = self._request(f"hsrl/ssjy/{stock_code}")
            # 麦蕊API返回的是列表，需要处理成字典格式
            if isinstance(data, list) and data:
                return {
                    'price': data[0].get('p', 0),
                    'open': data[0].get('o', 0),
                    'high': data[0].get('h', 0),
                    'low': data[0].get('l', 0),
                    'volume': data[0].get('v', 0)
                }
            return {}
        except (KeyError, IndexError):
            return {}

    def get_history_klines(self, stock_code: str, period: str = "dq") -> List[Dict]:
        """获取历史K线数据
        
        Args:
            stock_code: 股票代码
            period: K线周期,默认日线前复权
            
        Returns:
            List[Dict]: K线数据列表
        """
        return self._request(f"hszbl/fsjy/{stock_code}/{period}")

    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, str]]:
        """获取股票基本信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Optional[Dict[str, str]]: 股票基本信息，包含名称、行业、主营业务等。
            如果未找到股票信息则返回 None
        """
        try:
            # 调用麦蕊API获取股票信息
            data = self._request(f"hszl/gpxx/{stock_code}")
            if not data:
                print(f"未找到股票 {stock_code} 的基本信息")
                return None
                
            # 解析API返回的数据
            stock_info = data[0] if isinstance(data, list) and data else {}
            return {
                'code': stock_code,
                'name': stock_info.get('name', '未知'),
                'industry': stock_info.get('industry', '未知行业'),
                'main_business': stock_info.get('business', '暂无描述')
            }
            
        except Exception as e:
            print(f"获取股票信息时出错: {str(e)}")
            return None

    def get_top_holders(self, stock_code: str) -> List[Dict]:
        """获取前十大股东
        
        Args:
            stock_code: 股票代码
            
        Returns:
            List[Dict]: 股东信息列表
        """
        try:
            data = self._request(f"hscp/sdgd/{stock_code}")
            if isinstance(data, list) and data and 'sdgd' in data[0]:
                holders = data[0]['sdgd']
                return [
                    {
                        'name': holder.get('gdmc', ''),  # 股东名称
                        'ratio': holder.get('cgbl', 0),  # 持股比例
                        'shares': holder.get('cgsl', 0),  # 持股数量
                        'type': holder.get('gbxz', '')   # 股本性质
                    }
                    for holder in holders
                ]
            return []
        except (KeyError, IndexError):
            return []