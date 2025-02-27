from typing import Dict, Any, Optional
from .portfolio_manager import PortfolioManager

class PortfolioCLIManager:
    @staticmethod
    def get_initial_balance() -> float:
        """从用户输入获取初始资金"""
        while True:
            try:
                balance_input = input('请输入初始资金（例如：100000）：')
                balance = float(balance_input)
                if balance > 0:
                    return balance
                print('初始资金必须大于0')
            except ValueError:
                print('请输入有效的数字')
    
    @staticmethod
    def get_positions() -> Dict[str, Dict[str, Any]]:
        """从用户输入获取初始持仓信息"""
        positions = {}
        print('请输入持仓信息（每行一个，输入空行结束）')
        print('格式示例：000001.SZ,1000,10.5')
        print('说明：股票代码,持仓数量,成本价')
        
        while True:
            position_input = input('请输入持仓（或直接回车结束）：').strip()
            if not position_input:
                break
                
            try:
                ts_code, quantity, price = position_input.split(',')
                positions[ts_code.strip()] = {
                    'quantity': int(quantity),
                    'avg_price': float(price),
                    'last_update': ''
                }
            except ValueError:
                print('输入格式错误，请按照示例格式重新输入')
                continue
        
        return positions
    
    @classmethod
    def initialize_portfolio(cls) -> PortfolioManager:
        """初始化投资组合"""
        initial_balance = cls.get_initial_balance()
        portfolio_manager = PortfolioManager(initial_balance)
        
        # 获取并设置初始持仓
        positions = cls.get_positions()
        for ts_code, position in positions.items():
            portfolio_manager.add_position(
                ts_code,
                position['avg_price'],
                position['quantity']
            )
        
        return portfolio_manager
    
    @classmethod
    def test_cli_interaction(cls):
        """测试CLI交互功能"""
        print('开始测试CLI交互功能...')
        print('\n1. 测试初始资金输入:')
        portfolio = cls.initialize_portfolio()
        print(f'初始资金: {portfolio.get_available_balance()}')
        
        print('\n2. 测试持仓信息:')
        positions = portfolio.get_all_positions()
        if positions:
            print('当前持仓:')
            for ts_code, position in positions.items():
                print(f'股票代码: {ts_code}')
                print(f'持仓数量: {position["quantity"]}')
                print(f'平均成本: {position["avg_price"]}')
                print(f'最后更新: {position["last_update"]}\n')
        else:
            print('当前没有持仓')
        
        print('测试完成!')
        return portfolio