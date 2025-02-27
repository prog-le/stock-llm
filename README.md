# AI 投资组合管理系统

这是一个基于人工智能的投资组合管理系统，利用机器学习和自然语言处理技术来优化投资决策。

## 功能特点

- 股票数据采集和分析
- 金融新闻数据整合
- AI驱动的股票选择策略
- 自动化投资组合管理
- 风险评估和控制

## 项目结构

## 核心功能

### 1. 智能分析
- 个股深度分析
  - 基本面分析
  - 财务数据分析
  - 新闻情感分析
  - 行业前景分析
- 市场环境分析
  - 整体市场评估
  - 板块机会分析
  - 风险提示
- 交易建议生成
  - 买卖方向判断
  - 目标价格建议
  - 止损止盈设置
  - 持仓时间建议
  - 风险等级评估

### 2. 数据集成
- 实时行情数据 (迈瑞API)
- 财务报表数据 (Tushare)
- 新闻资讯 (新浪财经)
- 基本面数据
- 历史交易数据

### 3. 智能决策
- 投资组合管理
- 交易策略生成
- 风险控制
- 自动化交易执行

## 技术架构

### 核心模块
- `src/data/`: 数据获取和处理
  - `stock_data.py`: 股票数据获取
  - `news_data.py`: 新闻数据爬取
  - `financial_data.py`: 财务数据处理
  - `database.py`: 数据持久化
- `src/llm/`: 大模型集成
  - `model_api.py`: LLM服务接口
  - `stock_selector.py`: 智能选股
  - `strategy_generator.py`: 策略生成
- `src/portfolio/`: 投资组合
  - `portfolio_manager.py`: 组合管理
  - `trade_executor.py`: 交易执行

### 依赖组件
- Python 3.10
- DashScope (通义千问/DeepSeek)
- SQLite3
- Tushare
- BeautifulSoup4
- Requests

## 快速开始

### 1. 环境准备
- 克隆项目
- git clone https://github.com/prog-le/stock-llm.git
- cd stock-llm
- 安装依赖
- pip install -r requirements.txt

### 2. 配置设置
- 修改 `.env` 文件：
- `DASHSCOPE_API_KEY=your_api_key_here`
- `TUSHARE_TOKEN=your_token_here`
- `MAIRUI_LICENSE=your_license_here`

### 3. 运行程序
建议使用conda
- conda create --name stock-llm python=3.10
- conda activate stock-llm
- python main.py

## 注意事项

1. API 使用限制
   - DashScope API 调用频率限制
   - 新浪财经爬虫访问限制
   - 迈瑞数据 API 授权限制

2. 数据安全
   - API 密钥安全存储
   - 本地数据库备份
   - 敏感信息加密

3. 免责声明
   - 投资建议仅供参考
   - 市场风险提示
   - 实际交易需谨慎

## 开发计划

- [ ] 支持更多数据源接入
- [ ] 优化策略生成算法
- [ ] 添加回测功能
- [ ] 实现实盘交易接口
- [ ] 优化风险控制模型
- [ ] 增加 Web 界面

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交代码
4. 发起 Pull Request

## 许可证

MIT License

## 联系方式

- 作者：[Prog.le]
- 邮箱：[Prog.le@outlook.com]
- 项目地址：[https://github.com/prog-le/stock-llm]
