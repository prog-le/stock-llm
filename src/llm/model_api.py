import os
import dashscope
import re
from typing import Dict, Any, List
from datetime import datetime
from ..data import MaiRuiStockAPI, NewsDataFetcher  # 添加需要的导入

class LLMService:
    """大模型服务接口"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        dashscope.api_key = api_key
    
    def analyze_stock(self, stock_info: Dict[str, Any], news_list: List[Dict], 
                     financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析股票投资价值"""
        try:
            # 构建提示词
            prompt = self._build_analysis_prompt(stock_info, news_list, financial_data)
            print("\n发送给模型的提示词:")
            print("-" * 50)
            print(prompt)
            print("-" * 50)
            
            # 调用模型
            response = dashscope.Generation.call(
                model='qwen-max',  # 使用通义千问Max模型
                messages=[{
                    'role': 'system',
                    'content': '你是一个专业的股票分析师，擅长分析公司基本面、行业前景和财务数据。'
                }, {
                    'role': 'user',
                    'content': prompt
                }],
                result_format='message',  # 返回格式为消息
                temperature=0.7,  # 控制生成的随机性
                max_tokens=1500,  # 最大生成长度
                top_p=0.8,  # 控制生成的多样性
                enable_search=True,  # 启用搜索增强
            )
            
            print("\n模型原始响应:")
            print(response)
            
            if response.status_code == 200:
                # 从响应中提取文本
                if hasattr(response.output, 'choices') and response.output.choices:
                    analysis = response.output.choices[0].message.content
                else:
                    analysis = response.output.text
                    
                if not analysis:
                    return {
                        'error': "模型返回的分析内容为空",
                        'timestamp': datetime.now().isoformat(),
                        'status': 'error'
                    }
                    
                # 解析交易建议
                trading_advice = self._parse_trading_advice(analysis)
                
                return {
                    'analysis': analysis,
                    'trading_advice': trading_advice,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success'
                }
            else:
                return {
                    'error': f"API调用失败: {response.code} - {response.message}",
                    'timestamp': datetime.now().isoformat(),
                    'status': 'error'
                }
                
        except Exception as e:
            import traceback
            error_msg = f"调用模型时出错: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return {
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }
    
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
            # 构建提示词
            prompt = f"""请分析当前市场机会并给出具体的交易建议：

1. 最新市场新闻：
"""
            for i, news in enumerate(news_list[:5], 1):
                prompt += f"""
新闻{i}:
标题: {news.get('title')}
时间: {news.get('time')}
内容: {news.get('content')}
"""
            
            prompt += f"""
2. 可用资金：{available_cash}元

请从以下几个方面进行分析：
1. 市场整体环境
2. 主要投资机会
3. 风险提示
4. 具体投资建议，请列出3-5只推荐关注的股票，每只股票都需要包含以下信息：

推荐股票清单：
1. 第一支股票
   - 股票代码：xxx
   - 股票名称：xxx
   - 所属行业：xxx
   - 推荐理由：xxx
   - 建议买入价格：xx.xx元
   - 建议买入数量：xxxx股
   - 止损价格：xx.xx元
   - 目标价格：xx.xx元
   - 预期持有期：xx个交易日
   - 风险等级：高/中/低

2. 第二支股票
   ...（按相同格式列出）

请确保建议具体、明确、可执行，并说明主要风险因素。
"""
            
            # 调用模型
            response = dashscope.Generation.call(
                model='qwen-max',
                messages=[{
                    'role': 'system',
                    'content': '你是一个专业的投资顾问，擅长分析市场机会和制定投资策略。'
                }, {
                    'role': 'user',
                    'content': prompt
                }],
                result_format='message',
                temperature=0.7,
                max_tokens=1500,
                top_p=0.8,
                enable_search=True,
            )
            
            print("\n市场分析原始响应:")
            print(response)
            
            if response.status_code == 200:
                if hasattr(response.output, 'choices') and response.output.choices:
                    analysis = response.output.choices[0].message.content
                else:
                    analysis = response.output.text
                    
                if not analysis:
                    return {
                        'error': "模型返回的分析内容为空",
                        'timestamp': datetime.now().isoformat(),
                        'status': 'error'
                    }
                    
                return {
                    'analysis': analysis,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success'
                }
            else:
                return {
                    'error': f"API调用失败: {response.code} - {response.message}",
                    'timestamp': datetime.now().isoformat(),
                    'status': 'error'
                }
                
        except Exception as e:
            import traceback
            error_msg = f"调用模型时出错: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return {
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

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