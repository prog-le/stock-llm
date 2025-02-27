from typing import List, Dict, Any
from datetime import datetime

class PortfolioManager:
    def __init__(self, initial_balance: float):
        """初始化资金池"""
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
    
    def get_available_balance(self) -> float:
        """获取可用资金"""
        return self.current_balance
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """获取总资产价值"""
        portfolio_value = self.current_balance
        
        for ts_code, position in self.positions.items():
            if ts_code in current_prices:
                portfolio_value += position['quantity'] * current_prices[ts_code]
        
        return portfolio_value
    
    def add_position(self, ts_code: str, price: float, quantity: int) -> bool:
        """添加持仓"""
        cost = price * quantity
        if cost > self.current_balance:
            return False
        
        if ts_code in self.positions:
            # 更新现有持仓
            old_position = self.positions[ts_code]
            total_quantity = old_position['quantity'] + quantity
            avg_price = (old_position['avg_price'] * old_position['quantity'] + price * quantity) / total_quantity
            
            self.positions[ts_code] = {
                'quantity': total_quantity,
                'avg_price': avg_price,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            # 创建新持仓
            self.positions[ts_code] = {
                'quantity': quantity,
                'avg_price': price,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        self.current_balance -= cost
        self._record_trade('buy', ts_code, price, quantity)
        return True
    
    def reduce_position(self, ts_code: str, price: float, quantity: int) -> bool:
        """减少持仓"""
        if ts_code not in self.positions or self.positions[ts_code]['quantity'] < quantity:
            return False
        
        self.positions[ts_code]['quantity'] -= quantity
        if self.positions[ts_code]['quantity'] == 0:
            del self.positions[ts_code]
        
        self.current_balance += price * quantity
        self._record_trade('sell', ts_code, price, quantity)
        return True
    
    def get_position(self, ts_code: str) -> Dict[str, Any]:
        """获取持仓信息"""
        return self.positions.get(ts_code, {})
    
    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有持仓信息"""
        return self.positions
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """获取交易历史"""
        return self.trade_history
    
    def _record_trade(self, action: str, ts_code: str, price: float, quantity: int) -> None:
        """记录交易"""
        self.trade_history.append({
            'action': action,
            'ts_code': ts_code,
            'price': price,
            'quantity': quantity,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })