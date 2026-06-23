# AI 投资组合管理系统

> **一个 7×24 跟不上的散户的"AI 投顾 CLI"**——每天 30 秒拿到持仓日报和市场机会，但不会替你做决策，也不会替你赚钱。

## 项目愿景（最终实现目标）

本项目最终要成为散户的**私人 AI 投顾工作流**，围绕三个用户场景展开：

### 场景 1：盘后 30 秒拿到"持仓日报"
跑一次 `python main.py`，对每只持仓股得到：AI 解读（结合 7 天新闻 + 财务）+ 一张交易建议表（方向 / 目标价 / 止损 / 止盈 / 持仓周期 / 风险等级）。自动存 SQLite，可回看。

> 价值：替代刷雪球 / 看研报的 1-2 小时

### 场景 2：周末"扫一遍市场机会"
账户里还有闲钱？AI 拉 40 条市场新闻 → 推荐 3-5 只股票 → 拉详情 + 实时价 + 财务 + 技术指标 → 给每只的买卖建议 + 仓位建议。

> 价值：替代券商月度策略会 + 同花顺"问财"

### 场景 3：回看"AI 当时怎么说的"
SQLite 里按时间倒序查历史，验证 AI 的判断准不准——这是建立"AI 投顾日志"的关键。

> 价值：跟踪 AI 推荐准确率，从历史中学习

### 项目**不**承诺的
- ❌ 不会自动下单（无券商 API 对接）
- ❌ 不是实时监控（需手动 `python main.py`）
- ❌ 当前没有回测验证（按 AI 建议过去 1 年赚了多少）
- ❌ 不是 Web / 移动端（纯 CLI）
- ❌ **不替你做决策、不替你赚钱**——投资建议仅供参考

## 功能特点

- 股票数据采集和分析
- 金融新闻数据整合
- AI驱动的股票选择策略
- 自动化投资组合管理
- 风险评估和控制

## 项目结构

## 核心功能

> 功能描述以**用户能感知到的输出**为主，技术细节看各模块源码。

### 1. 个股深度分析
- **输入**：股票代码、持仓信息、7 天新闻、财务数据、实时价
- **输出**：
  - 整体分析 + 基本面 + 行业前景 + 新闻影响 + 财务点评
  - 结构化交易建议（7 个字段：方向 / 目标价 / 数量 / 止损 / 止盈 / 持仓天数 / 风险等级）
  - 存到 `stock_analysis` 表
- **对应场景**：场景 1（持仓日报）

### 2. 市场机会扫描
- **输入**：当日市场新闻、可用资金
- **输出**：
  - 第一步：推荐 3-5 只股票（含代码、名称、推荐理由）
  - 第二步：拉每只详情
  - 第三步：综合分析给买卖建议 + 仓位策略
  - 存到 `market_analysis` 表
- **对应场景**：场景 2（市场机会扫描）

### 3. 历史档案
- **存储**：SQLite 4 张表
  - `stock_analysis` — 个股分析快照
  - `market_analysis` — 市场分析快照
  - `news_data` — 新闻数据
  - `stock_info` — 股票元信息
- **查询**：标准 SQL 即可回看
- **对应场景**：场景 3（回看历史）

## 技术架构

### 核心模块
- `src/data/`: 数据获取和处理
  - `stock_data.py`: 股票数据获取
  - `news_data.py`: 新闻数据爬取
  - `financial_data.py`: 财务数据处理
  - `database.py`: 数据持久化（SQLite）
- `src/llm/`: 大模型集成
  - `model_api.py`: LLM服务接口（Instructor + Pydantic v2 结构化输出）
  - `schemas.py`: 8 个 pydantic 模型（TradingAdvice / StockAnalysis / MarketAnalysis 等）
- `src/portfolio/`: 投资组合
  - `portfolio_manager.py`: 内存级组合管理（资金 / 加权均价 / 交易历史）
- `src/tui/`: Textual TUI 界面（`python -m src.tui.app` 启动）
  - `app.py`: 主框架 + 4 个 tab（持仓 / 市场 / 配置 / 行情）
  - `screens/`: 4 个 Screen（portfolio / market / config / realtime）
  - `widgets/`: 复用组件（HoldingsSidebar / PortfolioStore）
- `tests/`: 221 个测试（`pytest`）

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

两种入口：
- **CLI 一次性分析**：`python main.py`（场景 1 + 场景 2，结果打到 stdout + SQLite）
- **TUI 交互界面**：`python -m src.tui.app`（4 个 tab：持仓 / 市场 / 配置 / 行情）

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

## 路线图（按阶段交付）

按"**先可信 → 后扩展**"分三步。每步独立可用、可回滚。

### 阶段 1：让 AI 输出可信（本次 PR 进行中）
- 引入 Instructor + Pydantic v2，LLM 输出结构化
- 干掉 6 个手写正则 / 重复技术指标方法
- 实时价注入 prompt
- 结构化错误返回（`error_type` 分类）
- **对用户场景的价值**：让"持仓日报"和"市场扫描"两个场景的输出**值得依赖**

### 阶段 2：基础设施替换（数据源 / 工具 / 持久化 / 缓存）
- AKShare 替代麦蕊（统一行情 / 财务 / 板块数据源，**免 LICENSE**）
- newspaper3k 替代手写新浪爬虫
- pandas-ta 替代手算技术指标
- Loguru 替代 print
- pydantic-settings 集中管理配置
- SQLAlchemy + Alembic 替代裸 sqlite3 + 手写迁移
- DiskCache 加 TTL 缓存层
- **对用户场景的价值**：让"日报"运行更便宜（省 API 配额）、更稳定（防反爬）

### 阶段 3：能力扩展（验证 / 仓位 / 多端）
- PyPortfolioOpt 做仓位优化
- vectorbt 或 Qlib 做回测（验证 AI 水平）
- Streamlit 做 Web 界面
- **对用户场景的价值**：补齐"回测验证"（场景 3 的关键），让产品从 CLI 玩具变成可用工具

### 交付节奏

每个微任务完成后：
1. **git commit 落盘** —— 该微任务独立可回滚
2. **位置分析** —— 写明"这一步在整个产品里的位置 / 和前后步骤的关系 / 它如何服务产品目标"
3. **报告** —— 把分析同步给用户
4. **确认** —— 用户确认后再进行下一步

**为什么串行而不是并行**：每步可独立验证、可独立回滚，避免一次性大爆炸；同时通过"位置分析"留下决策痕迹，未来回看 git log 就能复盘"为什么这一步在这个位置"。

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

### 支付宝捐赠
如果你觉得这个项目对你有帮助，可以通过支付宝进行捐赠：

