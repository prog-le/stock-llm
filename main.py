import os
from dotenv import load_dotenv
from typing import Dict, List, Any
from src.data import MaiRuiStockAPI, FinancialDataFetcher, NewsDataFetcher
from src.llm import LLMService
from src.portfolio import PortfolioManager, TradeExecutor
from src.data.database import DatabaseManager

def get_user_portfolio() -> Dict[str, float]:
    """获取用户持仓信息"""
    portfolio = {}
    print("\n请输入您的持仓信息（输入空股票代码结束）：")
    while True:
        stock_code = input("\n请输入股票代码（直接回车结束）: ").strip()
        if not stock_code:
            break
        try:
            shares = float(input("请输入持仓数量: "))
            cost = float(input("请输入成本价: "))
            portfolio[stock_code] = {'shares': shares, 'cost': cost}
        except ValueError:
            print("输入格式错误，请重新输入")
            continue
    return portfolio

def get_user_balance() -> float:
    """获取用户可用资金"""
    while True:
        try:
            balance = float(input("\n请输入可用资金（元）: "))
            return balance
        except ValueError:
            print("输入格式错误，请重新输入")

def format_trading_advice(advice: Dict[str, Any]) -> str:
    """格式化交易建议输出"""
    if not advice:
        return "无法解析具体交易建议"
        
    return f"""
具体交易建议:
------------------------
交易方向: {advice.get('direction', '未指定')}
目标价格: {advice.get('target_price', '未指定')} 元
交易数量: {advice.get('quantity', '未指定')} 股
止损价格: {advice.get('stop_loss', '未指定')} 元
止盈目标: {advice.get('take_profit', '未指定')} 元
建议持仓: {advice.get('holding_period', '未指定')} 个交易日
风险等级: {advice.get('risk_level', '未指定')}
------------------------"""

def analyze_portfolio(portfolio: Dict[str, float], 
                     balance: float,
                     stock_api: MaiRuiStockAPI,
                     news_api: NewsDataFetcher,
                     financial_api: FinancialDataFetcher,
                     llm_service: LLMService,
                     db: DatabaseManager) -> None:
    """分析投资组合"""
    
    # 1. 分析持仓股票
    if portfolio:
        print("\n=== 分析持仓股票 ===")
        for stock_code, position in portfolio.items():
            print(f"\n分析 {stock_code} ...")
            
            # 获取股票信息
            stock_info = stock_api.get_stock_info(stock_code)
            if not stock_info:
                print(f"无法获取股票 {stock_code} 的信息")
                continue
            
            # 保存股票信息
            db.save_stock_info(stock_info)
            
            # 获取相关新闻
            news_list = news_api.get_stock_news(stock_code, days=7)
            print(f"获取到 {len(news_list)} 条相关新闻")
            
            # 保存新闻
            db.save_news(news_list, stock_code)
            
            # 获取财务数据
            financial_data = financial_api.get_financial_data(stock_code)
            
            # 添加持仓信息到分析
            stock_info['position'] = position
            
            # 调用模型分析
            result = llm_service.analyze_stock(stock_info, news_list, financial_data)
            
            # 保存分析结果
            if result['status'] == 'success':
                result['stock_name'] = stock_info.get('name')
                db.save_stock_analysis(stock_code, result)
            
            print("\n分析结果:")
            print("-" * 50)
            if result['status'] == 'success':
                print(result['analysis'])
                print("\n" + format_trading_advice(result.get('trading_advice')))
            else:
                print(f"分析失败: {result.get('error')}")
            print("-" * 50)
            
            input("\n按Enter继续...")
    
    # 2. 分析市场机会
    print("\n=== 分析市场机会 ===")
    # 获取财经新闻
    market_news = news_api.get_daily_news(min_count=40)
    print(f"\n获取到 {len(market_news)} 条市场新闻")
    
    # 保存市场新闻
    db.save_news(market_news)
    
    # 调用模型分析市场机会
    market_analysis = llm_service.analyze_market(market_news, balance)
    
    # 保存市场分析结果
    if market_analysis['status'] == 'success':
        db.save_market_analysis(market_analysis, balance)
    
    print("\n市场分析结果:")
    print("-" * 50)
    if market_analysis['status'] == 'success':
        print(market_analysis['analysis'])
    else:
        print(f"分析失败: {market_analysis.get('error')}")
    print("-" * 50)

def main():
    # 1. 加载环境变量
    load_dotenv()
    api_key = os.getenv('DEEPSEEK_API_KEY')
    
    if not api_key:
        # 尝试从DASHSCOPE_API_KEY获取
        api_key = os.getenv('DASHSCOPE_API_KEY')
        if not api_key:
            raise ValueError("请在.env文件中设置DEEPSEEK_API_KEY或DASHSCOPE_API_KEY")
    
    # 2. 初始化组件
    print("初始化系统组件...")
    stock_api = MaiRuiStockAPI()
    financial_api = FinancialDataFetcher()
    news_api = NewsDataFetcher()
    llm_service = LLMService(api_key)
    
    # 初始化数据库
    db = DatabaseManager()
    
    # 3. 获取用户输入
    portfolio = get_user_portfolio()
    balance = get_user_balance()
    
    # 4. 分析投资组合和市场机会
    analyze_portfolio(
        portfolio=portfolio,
        balance=balance,
        stock_api=stock_api,
        news_api=news_api,
        financial_api=financial_api,
        llm_service=llm_service,
        db=db
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序运行出错: {str(e)}")