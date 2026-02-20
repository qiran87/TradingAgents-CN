# 交互索引

## 文档导航

本索引提供所有项目分析文档的快速导航，帮助开发者快速找到所需信息。

## 文档列表

| 序号 | 文档名称 | 文件路径 | 核心内容 |
|------|----------|----------|----------|
| 00 | 项目概述 | `00-overview.md` | 项目简介、技术栈、核心功能、目录结构 |
| 01 | 前端组件 | `01-frontend-components.md` | Vue 组件、Pinia Store、API 封装 |
| 02 | 后端 API | `02-backend-apis.md` | REST API、WebSocket、认证授权 |
| 03 | 领域模型 | `03-backend-domains.md` | Pydantic 模型、数据结构、验证规则 |
| 04 | 数据库结构 | `04-database-schemas.md` | MongoDB 集合、Redis 数据结构、索引设计 |
| 05 | 第三方依赖 | `05-third-party-deps.md` | Python 包、npm 包、版本管理 |
| 06 | 开发指南 | `06-dev-guide.md` | 环境搭建、添加功能、调试技巧 |
| 07 | 代码关系 | `07-code-relations.md` | 依赖关系、调用关系、数据流 |
| 08 | 架构模式 | `08-architecture-patterns.md` | 设计模式、架构原则、最佳实践 |
| 09 | 测试策略 | `09-testing-strategy.md` | 测试框架、测试用例、测试策略 |
| 10 | 质量报告 | `10-quality-reports.md` | 代码质量、性能质量、改进建议 |

## 按角色导航

### 后端开发者

推荐阅读顺序：
1. [项目概述](./00-overview.md) - 了解整体架构
2. [后端 API](./02-backend-apis.md) - 学习 API 设计
3. [领域模型](./03-backend-domains.md) - 理解数据结构
4. [数据库结构](./04-database-schemas.md) - 掌握数据库设计
5. [开发指南](./06-dev-guide.md) - 开始开发

### 前端开发者

推荐阅读顺序：
1. [项目概述](./00-overview.md) - 了解整体架构
2. [前端组件](./01-frontend-components.md) - 学习组件设计
3. [代码关系](./07-code-relations.md) - 理解数据流
4. [开发指南](./06-dev-guide.md) - 开始开发

### 策略开发者

推荐阅读顺序：
1. [项目概述](./00-overview.md) - 了解回测框架
2. [领域模型](./03-backend-domains.md) - 理解策略接口
3. [架构模式](./08-architecture-patterns.md) - 学习策略模式
4. [开发指南](./06-dev-guide.md) - 开发新策略

### 测试工程师

推荐阅读顺序：
1. [项目概述](./00-overview.md) - 了解系统功能
2. [测试策略](./09-testing-strategy.md) - 学习测试方法
3. [质量报告](./10-quality-reports.md) - 了解质量目标

## 按主题导航

### 回测框架

核心文档：
- [项目概述 - 回测引擎](./00-overview.md#1-回测引擎)
- [领域模型 - 回测状态](./03-backend-domains.md#3-回测引擎领域模型)
- [数据库结构 - 回测集合](./04-database-schemas.md#核心集合详解)
- [架构模式 - 策略模式](./08-architecture-patterns.md#4-策略模式-strategy-pattern)

### 策略开发

核心文档：
- [开发指南 - 添加新策略](./06-dev-guide.md#添加新策略)
- [架构模式 - 策略模式](./08-architecture-patterns.md#4-策略模式-strategy-pattern)
- [代码关系 - 策略系统](./07-code-relations.md#2-策略系统关系图)

### API 开发

核心文档：
- [后端 API - 完整列表](./02-backend-apis.md)
- [开发指南 - 添加新 API](./06-dev-guide.md#添加新-api-端点)
- [架构模式 - 分层架构](./08-architecture-patterns.md#1-分层架构)

### 前端开发

核心文档：
- [前端组件 - 组件列表](./01-frontend-components.md)
- [代码关系 - 前端数据流](./07-code-relations.md#3-前端状态管理数据流)
- [开发指南 - 添加新组件](./06-dev-guide.md#添加新前端组件)

## 快速查找

### 功能查找

| 功能 | 相关文档 | 章节 |
|------|----------|------|
| 启动回测 | [后端 API](./02-backend-apis.md#11-启动回测) | 1.1 |
| 查询状态 | [后端 API](./02-backend-apis.md#14-查询回测状态) | 1.4 |
| 获取结果 | [后端 API](./02-backend-apis.md#16-获取回测结果) | 1.6 |
| 策略列表 | [后端 API](./02-backend-apis.md#2-策略管理-api) | 2 |
| 保存参数 | [后端 API](./02-backend-apis.md#3-保存参数-api) | 3 |
| WebSocket | [后端 API](./02-backend-apis.md#110-websocket-进度推送) | 1.10 |

### 数据结构查找

| 数据结构 | 相关文档 | 集合/模型 |
|----------|----------|-----------|
| 回测任务 | [数据库结构](./04-database-schemas.md#1-backtest_tasks-回测任务) | backtest_tasks |
| 交易记录 | [数据库结构](./04-database-schemas.md#3-backtest_trades-交易记录) | backtest_trades |
| 回测结果 | [数据库结构](./04-database-schemas.md#4-backtest_results-回测结果) | backtest_results |
| 股票信息 | [数据库结构](./04-database-schemas.md#5-stock_info-股票基本信息) | stock_info |
| 行情数据 | [数据库结构](./04-database-schemas.md#6-stock_quotes-股票行情数据) | stock_quotes |

### 组件查找

| 组件 | 相关文档 | 文件位置 |
|------|----------|----------|
| 回测控制面板 | [前端组件](./01-frontend-components.md#11-回测模块组件重点) | BacktestControlPanel.vue |
| 回测结果展示 | [前端组件](./01-frontend-components.md#14-backtestresultsvue) | BacktestResults.vue |
| 交易日选择器 | [前端组件](./01-frontend-components.md#21-tradingdayrangepickervue) | TradingDayRangePicker.vue |
| 股票选择器 | [前端组件](./01-frontend-components.md#22-stockselectorvue) | StockSelector.vue |

## 关键概念索引

### 回测相关

- **BacktestEngine**: 回测执行引擎
  - [领域模型](./03-backend-domains.md#31-backteststate)
  - [代码关系](./07-code-relations.md#1-回测流程调用链)

- **BacktestState**: 回测状态管理
  - [领域模型](./03-backend-domains.md#31-backteststate)

- **TradingCostCalculator**: 交易费用计算
  - [领域模型](./03-backend-domains.md#2-交易费用计算器)

### 策略相关

- **BaseStrategy**: 策略基类
  - [架构模式](./08-architecture-patterns.md#4-策略模式-strategy-pattern)

- **StrategyRegistry**: 策略注册表
  - [代码关系](./07-code-relations.md#2-策略系统关系图)

- **DualMAStrategy**: 双均线策略
  - [领域模型](./03-backend-domains.md#2-策略领域模型)

### 数据相关

- **MongoDB 集合**: 数据存储
  - [数据库结构](./04-database-schemas.md#mongodb-数据库)

- **Redis 数据结构**: 缓存和队列
  - [数据库结构](./04-database-schemas.md#redis-数据结构)

- **Tushare/AKShare**: 数据源
  - [第三方依赖](./05-third-party-deps.md#数据源集成)

## 常见问题快速定位

### Q: 如何添加新策略？

**A**: 参考 [开发指南 - 添加新策略](./06-dev-guide.md#添加新策略)

### Q: 回测数据如何存储？

**A**: 参考 [数据库结构 - 回测集合](./04-database-schemas.md#核心集合详解)

### Q: WebSocket 如何推送进度？

**A**: 参考 [后端 API - WebSocket](./02-backend-apis.md#110-websocket-进度推送)

### Q: 如何调用回测 API？

**A**: 参考 [后端 API - 完整列表](./02-backend-apis.md)

### Q: 前端如何使用 Store？

**A**: 参考 [前端组件 - 状态管理](./01-frontend-components.md#6-状态管理pinia-stores)

### Q: 数据库索引如何设计？

**A**: 参考 [数据库结构 - 索引设计](./04-database-schemas.md#索引设计)

## 文档更新记录

| 日期 | 版本 | 更新内容 | 作者 |
|------|------|----------|------|
| 2024-02-05 | 1.0.0 | 初始版本，创建所有文档 | Claude Code |

## 反馈与贡献

如果您发现文档有任何问题或有改进建议，请：

1. 提交 Issue 到项目仓库
2. 直接修改文档并提交 PR
3. 在开发团队中讨论

## 附录

### 术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| 回测 | Backtest | 使用历史数据验证交易策略 |
| K线 | Candlestick | 股票价格的时间序列图表 |
| T+1 | T+1 Rule | 中国股市交易规则，当日买入次日才能卖出 |
| 金叉 | Golden Cross | 短期均线上穿长期均线 |
| 死叉 | Death Cross | 短期均线下穿长期均线 |
| JWT | JSON Web Token | 用于身份验证的 Token |
| WebSocket | WebSocket | 全双工通信协议 |
| MongoDB | MongoDB | 文档型数据库 |
| Redis | Redis | 内存数据库 |
| Pydantic | Pydantic | Python 数据验证库 |

### 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Vue 3 官方文档](https://vuejs.org/)
- [MongoDB 官方文档](https://docs.mongodb.com/)
- [Element Plus 官方文档](https://element-plus.org/)

### 相关链接

- 项目仓库: [TradingAgents-CN](https://github.com/your-repo)
- 问题反馈: [Issues](https://github.com/your-repo/issues)
- 更新日志: [CHANGELOG.md](../CHANGELOG.md)
