from typing import Dict, Any, Optional
from datetime import datetime
from .portfolio_manager import PortfolioManager
from ..data.stock_data import MaiRuiStockAPI

class TradeExecutor:
    def __init__(self, portfolio_manager: PortfolioManager, stock_data_fetcher: MaiRuiStockAPI):
        """初始化交易执行器"""
        self.portfolio_manager = portfolio_manager
        self.stock_data_fetcher = stock_data_fetcher
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
    
    def execute_strategy(self, strategy: Dict[str, Any], ts_code: str) -> bool:
        """执行交易策略"""
        if not self._validate_strategy(strategy):
            return False
        
        # 获取当前市场价格
        current_price = self._get_current_price(ts_code)
        if current_price is None:
            return False
        
        # 执行交易
        if strategy['action'] == 'buy':
            return self._execute_buy(ts_code, current_price, strategy)
        elif strategy['action'] == 'sell':
            return self._execute_sell(ts_code, current_price, strategy)
        
        return True
    
    def _validate_strategy(self, strategy: Dict[str, Any]) -> bool:
        """验证策略是否有效"""
        required_fields = ['action', 'quantity', 'price']
        return all(field in strategy for field in required_fields)
    
    def _get_current_price(self, ts_code: str) -> Optional[float]:
        """获取当前市场价格"""
        quote = self.stock_data_fetcher.get_realtime_quotes(ts_code)
        return float(quote.get('price', 0)) if quote else None
    
    def _execute_buy(self, ts_code: str, current_price: float, strategy: Dict[str, Any]) -> bool:
        """执行买入操作"""
        if strategy['price'] >= current_price:
            return self.portfolio_manager.add_position(ts_code, current_price, strategy['quantity'])
        return False
    
    def _execute_sell(self, ts_code: str, current_price: float, strategy: Dict[str, Any]) -> bool:
        """执行卖出操作"""
        if strategy['price'] <= current_price:
            return self.portfolio_manager.reduce_position(ts_code, current_price, strategy['quantity'])
        return False
    
    def cancel_pending_order(self, order_id: str) -> bool:
        """取消待执行的订单"""
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]
            return True
        return False
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态"""
        return self.pending_orders.get(order_id, {})