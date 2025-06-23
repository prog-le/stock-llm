import os
from openai import OpenAI
import re
import json
from typing import Dict, Any, List
from datetime import datetime
from ..data import MaiRuiStockAPI, NewsDataFetcher, FinancialDataFetcher  # 添加缺失的导入

class LLMService:
    """大模型服务接口"""
    
    def __init__(self, api_key: str):
        """初始化 DeepSeek API"""
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.stock_api = MaiRuiStockAPI()  # 初始化股票API
        self.financial_api = FinancialDataFetcher()  # 初始化财务数据API
        self.news_api = NewsDataFetcher()  # 初始化新闻API
    
    def analyze_stock(self, stock_info: Dict[str, Any], news_list: List[Dict], 
                     financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析股票投资价值"""
        try:
            # 构建提示词
            prompt = self._build_analysis_prompt(stock_info, news_list, financial_data)
            
            # 调用模型
            response = self.client.chat.completions.create(
                model="deepseek-reasoner",  # 使用 DeepSeek-R1 模型
                messages=[{
                    'role': 'system',
                    'content': '你是一个专业的股票分析师，擅长分析公司基本面、行业前景和财务数据。'
                }, {
                    'role': 'user',
                    'content': prompt
                }],
                temperature=0.7,
                max_tokens=1500,
                top_p=0.8,
            )
            
            analysis_content = response.choices[0].message.content
            trading_advice = self._parse_trading_advice(analysis_content)
            
            return {
                'analysis': analysis_content,
                'trading_advice': trading_advice,
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'error': f"分析失败: {str(e)}",
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }
    
    def _parse_recommended_stocks(self, response_text: str) -> List[str]:
        """从模型响应中解析推荐的股票代码"""
        # 使用正则表达式匹配6位数字的股票代码
        stock_codes = re.findall(r'\b\d{6}\b', response_text)
        # 返回去重后的股票代码列表
        return list(set(stock_codes))
        
    def _parse_trading_advice(self, analysis_text: str) -> Dict[str, Any]:
        """从分析文本中解析交易建议"""
        advice = {}
        
        # 提取交易方向
        direction_match = re.search(r'交易方向[:：]\s*(买入|卖出|持有)', analysis_text)
        if direction_match:
            advice['direction'] = direction_match.group(1)
            
        # 提取目标价格
        price_match = re.search(r'目标价格[:：]\s*([\d.]+)', analysis_text)
        if price_match:
            advice['target_price'] = float(price_match.group(1))
            
        # 提取交易数量
        quantity_match = re.search(r'交易数量[:：]\s*([\d.]+)', analysis_text)
        if quantity_match:
            advice['quantity'] = int(float(quantity_match.group(1)))
            
        # 提取止损价格
        stop_loss_match = re.search(r'止损价格[:：]\s*([\d.]+)', analysis_text)
        if stop_loss_match:
            advice['stop_loss'] = float(stop_loss_match.group(1))
            
        # 提取止盈目标
        take_profit_match = re.search(r'止盈目标[:：]\s*([\d.]+)', analysis_text)
        if take_profit_match:
            advice['take_profit'] = float(take_profit_match.group(1))
            
        # 提取持仓时间
        holding_period_match = re.search(r'持仓时间[:：]\s*([\d.]+)', analysis_text)
        if holding_period_match:
            advice['holding_period'] = int(float(holding_period_match.group(1)))
            
        # 提取风险等级
        risk_level_match = re.search(r'风险等级[:：]\s*(低|中|高)', analysis_text)
        if risk_level_match:
            advice['risk_level'] = risk_level_match.group(1)
            
        return advice
        
    def _build_analysis_prompt(self, stock_info: Dict[str, Any], 
                             news_list: List[Dict], 
                             financial_data: Dict[str, Any]) -> str:
        """构建分析提示词"""
        prompt = f"""请分析以下股票的投资价值并给出具体的交易建议：

1. 股票基本信息:
代码: {stock_info.get('code')}
名称: {stock_info.get('name')}
所属行业: {stock_info.get('industry')}
主营业务: {stock_info.get('main_business')}

2. 最新相关新闻:
"""
        
        for i, news in enumerate(news_list[:3], 1):
            prompt += f"""
新闻{i}:
标题: {news.get('title')}
时间: {news.get('time')}
内容: {news.get('content')}
"""
        
        prompt += f"""
3. 主要财务指标:
营业收入: {financial_data.get('revenue')}
净利润: {financial_data.get('net_profit')}
毛利率: {financial_data.get('gross_margin')}
ROE: {financial_data.get('roe')}

请从以下几个方面进行分析并给出具体建议：

1. 公司基本面分析
2. 行业发展前景
3. 最新消息影响
4. 财务指标分析
5. 具体交易建议

你必须严格按照以下格式给出交易建议（包含所有字段且不能为空）：

交易建议：
交易方向：[买入/卖出]
目标价格：[具体数字，单位：元]
交易数量：[具体数字，单位：股]
止损价格：[具体数字，单位：元]
止盈目标：[具体数字，单位：元]
持仓时间：[具体数字，单位：个交易日]
风险等级：[高/中/低]

注意：
1. 所有数值必须是具体的数字，不能使用范围或描述性语言
2. 价格必须精确到小数点后两位
3. 交易数量必须是100的整数倍
4. 持仓时间必须是具体的交易日数
5. 必须包含上述所有字段，且格式要完全一致

请先给出分析，然后在最后给出严格按照上述格式的交易建议。
"""
        return prompt 

    def analyze_market(self, news_list: List[Dict], available_cash: float) -> Dict[str, Any]:
        """分析市场机会"""
        try:
            # 第一步: 根据新闻分析推荐股票
            initial_prompt = f"""请分析以下最新市场新闻,并推荐3-5只值得关注的股票：

1. 最新市场新闻：
"""
            for i, news in enumerate(news_list[:10], 1):  # 增加到10条新闻
                initial_prompt += f"""
新闻{i}:
标题: {news.get('title')}
时间: {news.get('time')}
内容: {news.get('content')}
"""
            
            initial_prompt += """
请根据以上新闻分析当前市场环境，并推荐3-5只值得关注的股票。
对于每只推荐的股票，请提供：
1. 股票代码（格式为6位数字，如000001、600000等）
2. 推荐理由
3. 所属行业

注意：请不要假设或猜测股票的当前价格，我们会在后续分析中获取实时数据。
"""

            print("\n发送给模型的初始提示词:")
            print("-" * 50)
            print(initial_prompt)
            print("-" * 50)

            initial_response = self.client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[{
                    'role': 'system',
                    'content': '你是一个专业的投资顾问,请根据新闻信息推荐股票。请确保提供准确的股票代码（6位数字）。'
                }, {
                    'role': 'user',
                    'content': initial_prompt
                }]
            )

            print("\n模型初始响应:")
            print("-" * 50)
            print(initial_response.choices[0].message.content)
            print("-" * 50)

            # 解析推荐的股票代码
            recommended_stocks = self._parse_recommended_stocks(initial_response.choices[0].message.content)
            print(f"\n解析出的股票代码: {recommended_stocks}")
            
            if not recommended_stocks:
                return {
                    'error': "未能从模型响应中解析出有效的股票代码",
                    'timestamp': datetime.now().isoformat(),
                    'status': 'error'
                }
            
            # 第二步: 获取推荐股票的详细信息
            stock_details = []
            for stock_code in recommended_stocks:
                print(f"\n获取股票 {stock_code} 的详细信息...")
                details = self._get_stock_details(stock_code)
                if details:
                    stock_details.append(details)
                    print(f"成功获取 {stock_code} 的详细信息")
                else:
                    print(f"无法获取 {stock_code} 的详细信息")

            if not stock_details:
                return {
                    'error': "无法获取任何推荐股票的详细信息",
                    'timestamp': datetime.now().isoformat(),
                    'status': 'error'
                }

            # 第三步: 对推荐股票进行深入分析
            final_prompt = f"""请对以下股票进行深入分析并给出具体交易建议：

可用资金：{available_cash}元

推荐股票详细信息：
{json.dumps(stock_details, ensure_ascii=False, indent=2)}

请根据以上信息，从风险收益比、市场趋势和估值水平等方面进行分析，并给出具体的投资建议。
对于每只股票，请明确说明：
1. 是否值得投资
2. 建议买入价格区间
3. 目标价格
4. 建议持仓比例
5. 止损点

请以清晰、结构化的方式呈现分析结果。
    1. 基本面分析 - 基于公司情况,行业前景等
    2. 技术面分析 - 基于提供的技术指标
    3. 市场情绪分析 - 基于相关新闻
4. 风险提示 - 明确指出投资风险
5. 具体交易建议

交易建议必须包含:
- 建议买入价格区间（基于技术分析给出合理区间，不要假设当前价格）
- 建议买入数量（考虑可用资金和风险分散）
- 止损位（明确的价格点位）
- 止盈目标（明确的价格点位）
- 建议持仓时间
- 风险等级（高/中/低）

重要提示：
1. 不要假设或猜测当前股票价格，请基于提供的技术指标进行分析
2. 给出的买入价格区间必须合理，与技术指标相符
3. 交易建议必须具体、可执行，不要使用模糊表述
4. 请考虑资金管理，不要将全部资金投入单一股票
"""

            print("\n发送给模型的最终提示词:")
            print("-" * 50)
            print(final_prompt)
            print("-" * 50)

            final_response = self.client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[{
                    'role': 'system',
                    'content': '你是一个专业的投资顾问,请给出详细的分析和具体的交易建议。请不要假设股票的当前价格，而是基于提供的技术指标给出合理的买入区间。'
                }, {
                    'role': 'user',
                    'content': final_prompt
                }]
            )

            print("\n模型最终响应:")
            print("-" * 50)
            print(final_response.choices[0].message.content)
            print("-" * 50)

            return {
                'analysis': final_response.choices[0].message.content,
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }

        except Exception as e:
            import traceback
            error_msg = f"分析失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return {
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

    def _parse_recommended_stocks(self, content: str) -> List[str]:
        """从模型输出中解析推荐的股票代码"""
        # 使用正则表达式匹配股票代码
        stock_codes = re.findall(r'[036]\d{5}', content)
        return list(set(stock_codes))  # 去重

    def _get_stock_details(self, stock_code: str) -> Dict[str, Any]:
        """获取股票详细信息"""
        try:
            # 获取基本面信息
            basic_info = self.stock_api.get_stock_info(stock_code)
            
            # 获取最新财务指标
            financial_data = self.financial_api.get_financial_data(stock_code)
            
            # 获取相关新闻
            news = self.news_api.get_stock_news(stock_code, days=7)
            
            # 获取技术指标
            technical_indicators = self.stock_api.get_technical_indicators(stock_code)
            
            return {
                'basic_info': basic_info,
                'financial_data': financial_data,
                'news': news[:3],  # 只取最新的3条新闻
                'technical_indicators': technical_indicators
            }
        except Exception as e:
            print(f"获取股票 {stock_code} 详细信息失败: {str(e)}")
            return None

    def _parse_trading_advice(self, analysis_text: str) -> Dict[str, Any]:
        """从分析文本中解析出具体的交易建议"""
        try:
            advice = {
                'direction': None,
                'target_price': None,
                'quantity': None,
                'stop_loss': None,
                'take_profit': None,
                'holding_period': None,
                'risk_level': None,
                'raw_text': analysis_text
            }
            
            # 使用更精确的正则表达式匹配
            patterns = {
                'direction': r'交易方向：\s*(买入|卖出)',
                'target_price': r'目标价格：\s*(\d+\.?\d*)',
                'quantity': r'交易数量：\s*(\d+)',
                'stop_loss': r'止损价格：\s*(\d+\.?\d*)',
                'take_profit': r'止盈目标：\s*(\d+\.?\d*)',
                'holding_period': r'持仓时间：\s*(\d+)',
                'risk_level': r'风险等级：\s*(高|中|低)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, analysis_text)
                if match:
                    value = match.group(1)
                    if key in ['target_price', 'stop_loss', 'take_profit']:
                        advice[key] = float(value)
                    elif key in ['quantity', 'holding_period']:
                        advice[key] = int(value)
                    else:
                        advice[key] = value
            
            return advice
            
        except Exception as e:
            print(f"解析交易建议时出错: {str(e)}")
            return None

    def get_technical_indicators(self, stock_code: str) -> Dict[str, Any]:
        """获取技术指标"""
        try:
            # 获取K线数据
            klines = self._request(f"hsrl/kline/{stock_code}")
            
            # 计算技术指标
            ma5 = self._calculate_ma(klines, 5)
            ma10 = self._calculate_ma(klines, 10)
            ma20 = self._calculate_ma(klines, 20)
            
            return {
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'volume': klines[-1].get('v', 0),
                'turnover_rate': klines[-1].get('tr', 0)
            }
        except Exception as e:
            print(f"获取技术指标失败: {str(e)}")
            return {}

    def _calculate_ma(self, klines: List[Dict], period: int) -> float:
        """计算移动平均线"""
        if len(klines) < period:
            return 0
        
        closes = [float(k.get('c', 0)) for k in klines[-period:]]
        return sum(closes) / period