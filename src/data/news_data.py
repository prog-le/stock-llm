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

        主接口失败时自动降级到备用接口；主备都失败时返回 ``[]``
        而不是让异常逃逸（避免主流程被网络抖动打挂）。

        Args:
            endpoint: API端点

        Returns:
            List[Dict]: JSON响应数据；失败时返回空列表
        """
        url = f"{self.BASE_URL}/{endpoint}/{self.LICENSE}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            # 主接口失败（网络 / HTTP / JSON 解析）时尝试备用接口
            try:
                backup_url = f"{self.BACKUP_URL}/{endpoint}/{self.LICENSE}"
                response = self.session.get(backup_url)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as e:
                # 主备都失败：打印告警并返回空列表，让调用方走降级路径
                print(f"麦蕊 API 主备均失败 ({endpoint}): {e}")
                return []

    def get_daily_news(self, min_count: int = 20) -> List[Dict]:
        """获取每日财经新闻

        优先使用 Tanshu API（需 TANSHU_API_KEY），
        失败时自动降级到新浪财经免费 feed（无需 key）。

        Args:
            min_count: 最少获取的新闻条数

        Returns:
            List[Dict]: 新闻列表，每条含 title/content/source/time/url
        """
        api_key = os.getenv("TANSHU_API_KEY")
        if api_key:
            try:
                url = "https://api.tanshuapi.com/api/toutiao/v1/index"
                params = {
                    "key": api_key,
                    "type": "股票",
                    "num": max(min_count, 40),
                    "start": 0,
                }
                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if data.get("code") == 1:
                    news_list = []
                    for news in data.get("data", {}).get("list", []):
                        try:
                            item = {
                                "title": news.get("title", ""),
                                "content": news.get("content", ""),
                                "source": news.get("src", ""),
                                "time": news.get("time", ""),
                                "url": news.get("weburl", ""),
                            }
                            if item["title"] and item["content"]:
                                news_list.append(item)
                        except Exception:
                            continue
                    if news_list:
                        return news_list[:min_count]
                    print("Tanshu API 返回空列表，降级到新浪 feed")
                else:
                    print(f"Tanshu API 返回错误: {data.get('msg')}，降级到新浪 feed")
            except Exception as e:
                print(f"Tanshu API 请求失败: {e}，降级到新浪 feed")
        else:
            print("未配置 TANSHU_API_KEY，使用新浪财经免费 feed")

        # ── 备选：新浪财经免费新闻 feed ──
        return self._fetch_sina_daily_news(min_count)

    def _fetch_sina_daily_news(self, min_count: int = 20) -> List[Dict]:
        """使用新浪财经免费 feed 获取每日新闻（无需 API key）。"""
        try:
            url = "https://feed.mix.sina.com.cn/api/roll/get"
            params = {
                "pageid": "153",  # 新浪财经新闻
                "lid": "2516",    # 国内财经
                "knum": min_count,
                "page": "1",
            }
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://finance.sina.com.cn/",
            }
            response = requests.get(url, params=params, headers=headers, timeout=15)
            data = response.json()

            news_list = []
            for item in data.get("result", {}).get("data", []):
                try:
                    title = item.get("title", "").strip()
                    intro = item.get("intro", "").strip()
                    content = intro or title
                    if title:
                        news_list.append({
                            "title": title,
                            "content": content,
                            "source": item.get("media_name", "新浪财经"),
                            "time": item.get("ctime", ""),
                            "url": item.get("url", ""),
                        })
                except Exception:
                    continue

            if not news_list:
                print("新浪 feed 返回空列表，尝试备用页面抓取...")
                return self._scrape_sina_finance_page(min_count)

            print(f"新浪财经 feed 获取到 {len(news_list)} 条新闻")
            return news_list[:min_count]

        except Exception as e:
            print(f"新浪 feed 请求失败: {e}，尝试页面抓取...")
            return self._scrape_sina_finance_page(min_count)

    def _scrape_sina_finance_page(self, min_count: int = 20) -> List[Dict]:
        """终极备选：直接解析新浪财经首页的新闻列表。"""
        try:
            url = "https://finance.sina.com.cn/"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36"
                ),
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            news_list = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                title = a.text.strip()
                if not title or len(title) < 8:
                    continue
                if "finance.sina.com.cn" in href or "https://" in href:
                    news_list.append({
                        "title": title,
                        "content": title,
                        "source": "新浪财经",
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "url": href,
                    })
                    if len(news_list) >= min_count:
                        break

            print(f"新浪首页抓取到 {len(news_list)} 条新闻")
            return news_list[:min_count]

        except Exception as e:
            print(f"新浪首页抓取失败: {e}")
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