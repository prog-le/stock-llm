import sqlite3
from typing import Dict, List, Any
from datetime import datetime
import json
import os

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/stock_analysis.db"):
        """初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
        self._migrate_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建股票分析结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT,
                    analysis_data TEXT,
                    trading_advice TEXT,
                    timestamp DATETIME,
                    status TEXT,
                    UNIQUE(stock_code, timestamp)
                )
            """)
            
            # 创建市场分析结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_data TEXT,
                    available_cash REAL,
                    timestamp DATETIME
                )
            """)
            
            # 创建新闻数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT,
                    title TEXT,
                    content TEXT,
                    source TEXT,
                    news_time DATETIME,
                    fetch_time DATETIME,
                    url TEXT
                )
            """)
            
            # 创建股票基本信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    stock_code TEXT PRIMARY KEY,
                    stock_name TEXT,
                    industry TEXT,
                    main_business TEXT,
                    update_time DATETIME
                )
            """)
            
            conn.commit()
    
    def _migrate_db(self):
        """数据库迁移"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 检查是否需要添加 trading_advice 列
            cursor.execute("PRAGMA table_info(stock_analysis)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'trading_advice' not in columns:
                print("正在更新数据库结构...")
                # 创建临时表
                cursor.execute("""
                    CREATE TABLE stock_analysis_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        stock_code TEXT NOT NULL,
                        stock_name TEXT,
                        analysis_data TEXT,
                        trading_advice TEXT,
                        timestamp DATETIME,
                        status TEXT,
                        UNIQUE(stock_code, timestamp)
                    )
                """)
                
                # 复制旧数据
                cursor.execute("""
                    INSERT INTO stock_analysis_new 
                    (stock_code, stock_name, analysis_data, timestamp, status)
                    SELECT stock_code, stock_name, analysis_data, timestamp, status
                    FROM stock_analysis
                """)
                
                # 删除旧表
                cursor.execute("DROP TABLE stock_analysis")
                
                # 重命名新表
                cursor.execute("ALTER TABLE stock_analysis_new RENAME TO stock_analysis")
                
                conn.commit()
                print("数据库结构更新完成")
    
    def save_stock_analysis(self, stock_code: str, analysis_result: Dict[str, Any]):
        """保存股票分析结果"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 保存分析结果
            cursor.execute("""
                INSERT INTO stock_analysis 
                (stock_code, stock_name, analysis_data, trading_advice, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                stock_code,
                analysis_result.get('stock_name', ''),
                json.dumps(analysis_result.get('analysis', ''), ensure_ascii=False),
                json.dumps(analysis_result.get('trading_advice', {}), ensure_ascii=False),
                analysis_result.get('timestamp'),
                analysis_result.get('status')
            ))
            conn.commit()
    
    def save_market_analysis(self, analysis_result: Dict[str, Any], available_cash: float):
        """保存市场分析结果"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO market_analysis 
                (analysis_data, available_cash, timestamp)
                VALUES (?, ?, ?)
            """, (
                json.dumps(analysis_result, ensure_ascii=False),
                available_cash,
                analysis_result.get('timestamp')
            ))
            conn.commit()
    
    def save_news(self, news_list: List[Dict[str, Any]], stock_code: str = None):
        """保存新闻数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for news in news_list:
                cursor.execute("""
                    INSERT OR REPLACE INTO news_data 
                    (stock_code, title, content, source, news_time, fetch_time, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    stock_code,
                    news.get('title'),
                    news.get('content'),
                    news.get('source'),
                    news.get('time'),
                    datetime.now().isoformat(),
                    news.get('url')
                ))
            conn.commit()
    
    def save_stock_info(self, stock_info: Dict[str, Any]):
        """保存股票基本信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO stock_info 
                (stock_code, stock_name, industry, main_business, update_time)
                VALUES (?, ?, ?, ?, ?)
            """, (
                stock_info.get('code'),
                stock_info.get('name'),
                stock_info.get('industry'),
                stock_info.get('main_business'),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_latest_analysis(self, stock_code: str) -> Dict[str, Any]:
        """获取最新的股票分析结果"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT analysis_data FROM stock_analysis
                WHERE stock_code = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (stock_code,))
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
    
    def get_latest_market_analysis(self) -> Dict[str, Any]:
        """获取最新的市场分析结果"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT analysis_data FROM market_analysis
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None