# AI 智能聊天助手 — 技术方案文档

## 一、功能概述

AI 智能聊天助手是一个嵌入在行情页面中的智能分析组件，能够：

1. **页面感知分析**：自动获取当前页面的股票数据（K线、行情、财务、技术指标），基于真实数据给出技术面/基本面/情绪面分析
2. **止盈止损策略**：根据用户提供的持仓成本和数量，制定具体的止盈止损方案
3. **Action 系统**：AI 可以"抛出"动作指令（如设置止盈止损），经中间层处理后写入数据库并在 K 线图上可视化
4. **可扩展**：通过注册 Action Handler 的方式，轻松扩展新动作（加入自选、设置预警等）

## 二、架构总览

```
┌──────────────────────────────────────────────────────────────┐
│  前端 MarketPage                                              │
│  ┌─────────────────────────┐    ┌──────────────────────────┐ │
│  │ StockDetailPanel (K线图) │◄───│ AIChatPanel (悬浮抽屉)    │ │
│  │                         │    │                          │ │
│  │  监听 onActionExecuted  │    │  1. 用户输入 + 股票代码    │ │
│  │  收到后画 tp/sl/cost 线 │    │  2. SSE 流式请求后端       │ │
│  │                         │    │  3. 实时渲染 Markdown      │ │
│  └─────────────────────────┘    │  4. 解析 <action> 标签     │ │
│                                 │  5. 渲染 ActionCard 确认   │ │
│                                 └──────────────────────────┘ │
└────────────────────────────┬──────────────────────────────────┘
                             │ POST /api/chat/stream (SSE)
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  后端 FastAPI                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ chat.py     │──►│ chat_service │──►│ prompt_builder     │  │
│  │ (SSE路由)   │  │ (业务编排)    │  │ (读SQLite组装数据)  │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
│        │                              │                      │
│        │ POST /api/chat/actions       │                      │
│        ▼                              ▼                      │
│  ┌──────────────┐            ┌────────────────────────┐     │
│  │action_handler│            │ Anthropic API (智谱代理) │     │
│  │ (执行DB操作)  │            │ stream=true            │     │
│  └──────────────┘            └────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

## 三、技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | React 18 + TypeScript + Vite | |
| UI 组件库 | Ant Design 6（暗色主题） | |
| Markdown 渲染 | react-markdown + remark-gfm | GFM 语法支持 |
| 后端框架 | FastAPI + Pydantic v2 | |
| 数据库 | SQLite (WAL模式) + SQLAlchemy 2.0 | 约 13GB |
| AI SDK | anthropic (Python) | 兼容 Anthropic 格式代理 |
| 流式传输 | SSE (Server-Sent Events) | 前端 fetch + ReadableStream |

## 四、文件清单

### 后端文件

| 文件路径 | 功能 |
|---------|------|
| `server/config.py` | AI 模型配置（API Key / Base URL / Model） |
| `server/db/models.py` | `PositionTPSL` 止盈止损表 ORM 模型 |
| `server/models/chat.py` | 聊天 Pydantic 数据模型 |
| `server/services/ai_client.py` | Anthropic 格式 AI 客户端（流式） |
| `server/services/prompt_builder.py` | 从 SQLite 读数据 + 计算技术指标 + 组装 prompt |
| `server/services/action_handler.py` | Action 解析器 + Handler 注册机制 |
| `server/services/chat_service.py` | 聊天业务编排（prompt → AI → SSE） |
| `server/routers/chat.py` | `/api/chat/stream` + `/api/chat/actions` 路由 |

### 前端文件

| 文件路径 | 功能 |
|---------|------|
| `web/src/types/chat.ts` | 聊天类型定义 |
| `web/src/api/chat.ts` | SSE 流式请求 + Action 执行 API |
| `web/src/hooks/useChatStream.ts` | 流式消息管理 Hook |
| `web/src/components/ai-chat/AIChatPanel.tsx` | 聊天面板（悬浮抽屉） |
| `web/src/components/ai-chat/ChatMessage.tsx` | 单条消息渲染 |
| `web/src/components/ai-chat/ActionCard.tsx` | Action 确认卡片 |
| `web/src/components/ai-chat/SimpleMarkdown.tsx` | Markdown 渲染组件 |
| `web/src/pages/MarketPage.tsx` | 集成 AI 浮动按钮 + 画线联动 |
| `web/src/components/stock/StockDetailPanel.tsx` | 传递 extraMarkLines |
| `web/src/components/charts/KlineChart.tsx` | 支持 extraMarkLines 画标记线 |

## 五、数据流详解

### 5.1 聊天流程

```
1. 用户点击 AI 按钮 → 打开 AIChatPanel
2. 用户输入问题 → useChatStream.sendMessage()
3. 前端 POST /api/chat/stream (SSE)
4. 后端 chat_service.chat_stream():
   a. prompt_builder.build_stock_prompt(code) → 从 SQLite 读取:
      - 实时行情 (stock_daily 最新一条)
      - 近60天K线 → 计算 MA5/MA10/MA20/RSI/MACD/布林带
      - 财务数据 (stock_financial 最新一期)
      - 用户持仓 (如传入)
   b. ai_client.stream_chat(system_prompt, messages) → 流式调 AI
   c. SSE 逐块返回 → data: {"type":"text","content":"..."}
5. 前端 useChatStream 逐块拼接 → 实时渲染 Markdown
6. AI 回复完成 → 解析 <action> 标签 → 渲染 ActionCard
```

### 5.2 Action 执行流程

```
1. AI 回复末尾包含: <action type="set_tp_sl" data='{"tp_price":16.8,...}' />
2. 前端 parseActions() 从文本中提取 XML 标签
3. 渲染 ActionCard（显示止盈/止损价格 + 确认按钮）
4. 用户点击"确认执行" → POST /api/chat/actions
5. 后端 action_handler:
   a. 写入 position_tp_sl 表
   b. 返回 {success: true, data: {tp_price, sl_price, ...}}
6. 前端 onActionExecuted 回调 → MarketPage 收到事件
7. MarketPage 更新 extraMarkLines 状态
8. StockDetailPanel → KlineChart 渲染标记线:
   - 止盈线: 红色虚线
   - 止损线: 绿色虚线
   - 成本线: 蓝色实线
```

## 六、核心接口定义

### POST `/api/chat/stream` — SSE 流式对话

**请求:**
```json
{
  "code": "600519",
  "message": "分析一下走势，成本100元买了100股",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "position": {"cost": 100.0, "quantity": 100}
}
```

**响应 (SSE):**
```
data: {"type":"text","content":"## 贵州茅台(600519) 分析\n\n"}
data: {"type":"text","content":"### 技术面\n\n"}
...
data: {"type":"done"}
```

### POST `/api/chat/actions` — 执行 Action

**请求:**
```json
{
  "type": "set_tp_sl",
  "data": {"stock_code": "600519", "tp_price": 120, "sl_price": 90}
}
```

**响应:**
```json
{
  "success": true,
  "message": "✅ 已保存止盈止损：止盈 120 / 止损 90",
  "data": {"id": 1, "code": "600519", "tp_price": 120, "sl_price": 90}
}
```

## 七、数据库模型

### position_tp_sl 表（止盈止损记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| code | VARCHAR(10) | 股票代码 |
| cost_price | FLOAT | 参考成本价 |
| quantity | INTEGER | 参考持仓数量 |
| tp_price | FLOAT | 止盈价 |
| sl_price | FLOAT | 止损价 |
| strategy | VARCHAR(50) | 策略名称 |
| reason | TEXT | AI 分析理由 |
| status | VARCHAR(10) | active / triggered_tp / triggered_sl / cancelled |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

## 八、Prompt 设计

系统提示词由 `prompt_builder.py` 动态组装，包含以下结构化数据：

```
【当前行情】最新价、涨跌幅、开盘、最高、最低、成交量、成交额
【技术面】MA5/MA10/MA20、RSI(6)、MACD(DIF/DEA/柱)、布林带(上/中/下轨)
【基本面】报告期、营业总收入、净利润、每股收益
【近10日走势摘要】涨跌天数、区间振幅、逐日涨跌幅
【用户持仓】（如提供）成本价、持仓数量、浮动盈亏

+ 可用 Action 列表及 XML 格式说明
```

技术指标在后端实时计算（MA/RSI/MACD/布林带），数据来源于 SQLite 的 `stock_daily` 表。

## 九、Action 扩展指南

### 新增一个 Action 的步骤

**1. 后端注册 Handler（`server/services/action_handler.py`）**

```python
@register_action("set_alert")
async def handle_set_alert(data: dict) -> dict:
    """设置价格预警"""
    # 实现逻辑：保存到数据库、触发通知等
    return {"success": True, "message": "✅ 预警已设置"}
```

**2. 更新系统提示词（`server/services/prompt_builder.py`）**

在 prompt 中添加新的 Action 说明：
```
2. <action type="set_alert" data='{"stock_code":"600519","target_price":150,"direction":"up"}' />
```

**3. 前端渲染（自动）**

ActionCard 组件会自动渲染未知类型的 Action，显示 JSON 数据和确认按钮。如需自定义 UI，在 `ActionCard.tsx` 的 `renderContent` 中添加新的 case。

## 十、配置说明

### 环境变量（可选覆盖默认值）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| AI_API_KEY | 已预配置 | AI 服务 API Key |
| AI_BASE_URL | `https://aicoding-proxy.myunke.com/cn-cch` | AI 代理地址 |
| AI_MODEL | `glm-5` | 模型名称 |
| AI_TIMEOUT | `60` | 请求超时（秒） |

默认值已写在 `server/config.py` 中，无需额外配置即可使用。

## 十一、使用方式

1. 启动后端：`python -m server.run`
2. 启动前端：`cd web && npm run dev`
3. 打开行情页面，右下角出现 **AI** 浮动按钮
4. 点击打开聊天面板，输入问题
5. AI 分析后如给出止盈止损建议，点击"确认执行"
6. K 线图自动标注止盈/止损/成本线
