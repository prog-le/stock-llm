import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import re
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv
load_dotenv()

class NewsDataFetcher:
    """新闻数据获取器"""
    
    BASE_URL = "http://api.mairui.club"
    BACKUP_URL = "http://api1.mairui.club"
    LICENSE = os.getenv('MAIRUI_LICENSE')
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def _request(self, endpoint: str) -> List[Dict]:
        """发送API请求
        
        Args:
            endpoint: API端点
            
        Returns:
            List[Dict]: JSON响应数据
        """
        url = f"{self.BASE_URL}/{endpoint}/{self.LICENSE}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            # 主接口失败时尝试备用接口
            backup_url = f"{self.BACKUP_URL}/{endpoint}/{self.LICENSE}"
            response = self.session.get(backup_url)
            response.raise_for_status()
            return response.json()

    def get_daily_news(self, min_count: int = 20) -> List[Dict]:
        """获取每日财经新闻
        
        Args:
            min_count: 最少获取的新闻条数
            
        Returns:
            List[Dict]: 新闻列表，每条新闻包含标题、内容、来源、时间等信息
        """
        try:
            # 使用新的新闻API接口
            url = "https://api.tanshuapi.com/api/toutiao/v1/index"
            params = {
                "key": os.getenv("TANSHU_API_KEY"),
                "type": "股票",
                "num": max(min_count, 40),  # 确保获取足够的新闻
                "start": 0
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get("code") != 1:  # API返回错误
                print(f"获取新闻数据失败: {data.get('msg')}")
                return []
            
            news_list = []
            for news in data.get("data", {}).get("list", []):
                try:
                    news_item = {
                        'title': news.get('title', ''),
                        'content': news.get('content', ''),
                        'source': news.get('src', ''),
                        'time': news.get('time', ''),
                        'url': news.get('weburl', '')
                    }
                    if news_item['title'] and news_item['content']:
                        news_list.append(news_item)
                except Exception as e:
                    print(f"处理单条新闻数据时出错: {str(e)}")
                    continue

            if len(news_list) < min_count:
                print(f"警告：只获取到 {len(news_list)} 条新闻，少于要求的 {min_count} 条")
            
            return news_list[:min_count] if len(news_list) > min_count else news_list
            
        except Exception as e:
            print(f"获取新闻数据时出错: {str(e)}")
            return []

    def get_stock_news(self, stock_code: str, days: int = 7) -> List[Dict]:
        """获取个股新闻
        
        Args:
            stock_code: 股票代码
            days: 获取最近几天的新闻，默认7天
        """
        try:
            # 处理股票代码格式
            if stock_code.startswith('6'):
                sina_code = f'sh{stock_code}'
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                sina_code = f'sz{stock_code}'
            else:
                print(f"不支持的股票代码格式: {stock_code}")
                return []
            
            # 获取新闻列表页面
            list_url = f'https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{sina_code}.phtml'
            print(f"正在获取新闻列表，URL: {list_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'Referer': 'https://vip.stock.finance.sina.com.cn',
            }
            
            response = self.session.get(list_url, headers=headers, timeout=10)
            response.encoding = 'gb2312'  # 新浪财经使用 GB2312 编码
            
            # 解析新闻列表页面
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找新闻表格
            news_table = soup.find('table', {'id': 'con02-0'})
            if not news_table:
                print("未找到主新闻表格，尝试查找其他新闻链接...")
                news_links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if any(domain in href for domain in ['finance.sina.com.cn', 'sina.com.cn']) and '/' in href:
                        title = a.text.strip()
                        if title and len(title) > 5:  # 过滤掉太短的标题
                            news_links.append({
                                'title': title,
                                'url': href if href.startswith('http') else f'https:{href}'
                            })
            else:
                # 从表格中提取新闻链接
                news_links = []
                for row in news_table.find_all('tr')[1:]:  # 跳过表头
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        link = cols[1].find('a')
                        if link and link.has_attr('href'):
                            title = link.text.strip()
                            url = link['href']
                            if title and url:
                                news_links.append({
                                    'title': title,
                                    'url': url if url.startswith('http') else f'https:{url}'
                                })
            
            if not news_links:
                print(f"未找到股票 {stock_code} 的相关新闻链接")
                return []
            
            print(f"找到 {len(news_links)} 条新闻链接，获取最新的10条新闻内容...")
            
            # 获取每条新闻的详细内容
            news_list = []
            for news in news_links[:10]:  # 限制获取最新的10条新闻
                try:
                    print(f"\n正在获取新闻: {news['title']}")
                    print(f"URL: {news['url']}")
                    
                    content = self._fetch_news_content(news['url'])
                    if content and len(content) > 100:  # 确保内容有足够长度
                        news_list.append({
                            'title': news['title'],
                            'content': content,
                            'url': news['url'],
                            'time': datetime.now().strftime('%Y-%m-%d'),  # 使用当前日期
                            'source': '新浪财经'
                        })
                        print(f"✓ 成功获取新闻内容 ({len(content)} 字)")
                    else:
                        print("✗ 新闻内容太短或获取失败")
                except Exception as e:
                    print(f"✗ 获取新闻失败: {str(e)}")
                    continue
                
                # 添加延时，避免请求过快
                time.sleep(1)
            
            print(f"\n成功获取 {len(news_list)} 条完整新闻")
            return news_list
            
        except Exception as e:
            print(f"获取股票新闻失败: {str(e)}")
            return []

    def _fetch_news_content(self, url: str) -> str:
        """获取新闻内容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'Referer': 'https://vip.stock.finance.sina.com.cn',
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            
            # 自动检测编码
            if 'charset=gb2312' in response.text or 'charset=GB2312' in response.text:
                response.encoding = 'gb2312'
            else:
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试多个可能的新闻内容容器
            content_selectors = [
                {'id': 'artibody'},
                {'class_': 'article-content'},
                {'class_': 'article'},
                {'class_': 'content'},
                {'id': 'article_content'},
                {'class_': 'main-content'},
            ]
            
            for selector in content_selectors:
                content_div = soup.find('div', **selector)
                if content_div:
                    # 移除不需要的元素
                    for unwanted in content_div.find_all(['script', 'style', 'iframe', 'div', 'table']):
                        unwanted.decompose()
                    
                    # 获取段落文本
                    paragraphs = []
                    for p in content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                        text = p.get_text(strip=True)
                        if text and len(text) > 10:  # 过滤掉太短的段落
                            paragraphs.append(text)
                    
                    if paragraphs:
                        content = ' '.join(paragraphs)
                        content = re.sub(r'\s+', ' ', content)
                        return content[:2000]  # 限制内容长度
            
            return ""
            
        except Exception as e:
            print(f"获取新闻内容失败 {url}: {str(e)}")
            return ""