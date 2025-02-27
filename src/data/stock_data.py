import requests
import json
from typing import Dict, List, Optional

class MaiRuiStockAPI:
    """麦蕊股票数据API封装"""
    
    BASE_URL = "http://api.mairui.club"
    BACKUP_URL = "http://api1.mairui.club"
    LICENSE = "8507084C-C56F-432E-8C43-FA40669B024B"

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

    def get_stock_info(self, stock_code: str) -> Dict[str, str]:
        """获取股票基本信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Dict: 股票基本信息，包含名称、行业、主营业务等
        """
        try:
            # 由于接口限制，这里返回模拟数据
            # 后续可以接入实际的股票信息API
            industry_map = {
                '600626': '房地产开发',
                '003032': '新能源汽车',
                '000001': '银行',
                '600000': '银行',
                # 可以添加更多股票的行业映射
            }
            
            name_map = {
                '600626': '申达股份',
                '003032': '传智教育',
                '000001': '平安银行',
                '600000': '浦发银行',
                # 可以添加更多股票的名称映射
            }
            
            business_map = {
                '600626': '主要从事房地产开发、物业管理等业务',
                '003032': '主要从事教育培训、在线教育等业务',
                '000001': '主要从事商业银行业务，包括公司业务、零售业务和金融市场业务等',
                '600000': '主要从事商业银行业务，包括公司金融、零售金融和金融市场业务等',
                # 可以添加更多股票的主营业务描述
            }
            
            if stock_code not in name_map:
                print(f"警告：未找到股票 {stock_code} 的基本信息，尝试实时获取...")
                # 这里可以添加实时获取股票信息的逻辑
                return {
                    'code': stock_code,
                    'name': f'未知股票_{stock_code}',
                    'industry': '未知行业',
                    'main_business': '暂无描述'
                }
            
            return {
                'code': stock_code,
                'name': name_map.get(stock_code, '未知'),
                'industry': industry_map.get(stock_code, '未知行业'),
                'main_business': business_map.get(stock_code, '暂无描述')
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