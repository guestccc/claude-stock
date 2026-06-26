# AI 智能聊天助手 — 技术方案文档

## 一、功能概述

AI 智能聊天助手是一个嵌入在行情页面中的智能分析组件，能够：

1. **页面感知分析**：自动获取当前页面的股票数据（K线、行情、财务、技术指标），基于真实数据给出技术面/基本面/情绪面分析
2. **止盈止损策略**：根据用户提供的持仓成本和数量，制定具体的止盈止损方案
3. **Action 系统**：AI 可以"抛出"动作指令（如设置止盈止损、压力支撑位），经中间层处理后写入数据库并在 K 线图上可视化
4. **可扩展（注册表模式）**：新增 Action 只需一个 handler 文件 + 一行注册，前后端均自动适配

## 二、架构总览

```
┌──────────────────────────────────────────────────────────────┐
│  前端 MarketPage                                              │
│  ┌─────────────────────────┐    ┌──────────────────────────┐ │
│  │ StockDetailPanel (K线图) │◄───│ AIChatPanel (悬浮抽屉)    │ │
│  │                         │    │                          │ │
│  │  extraMarkLines         │    │  1. 用户输入 + 股票代码    │ │
│  │  → ECharts markLine     │    │  2. SSE 流式请求后端       │ │
│  │  由 registry.ts 生成     │    │  3. 实时渲染 Markdown      │ │
│  └─────────────────────────┘    │  4. 解析 <action> 标签     │ │
│                                 │  5. ActionCard → 注册表路由 │ │
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
│  ┌──────────────────┐      ┌────────────────────────┐       │
│  │ action_handler   │      │ Anthropic API (智谱代理) │       │
│  │ → action_registry│      │ stream=true            │       │
│  │ → handlers/*.py  │      └────────────────────────┘       │
│  └──────────────────┘                                        │
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
| `server/db/models.py` | ORM 模型：`PositionTPSL`、`SupportResistance` 等 |
| `server/models/chat.py` | 聊天 Pydantic 数据模型（含 ActionResult） |
| `server/services/ai_client.py` | Anthropic 格式 AI 客户端（流式） |
| `server/services/prompt_builder.py` | 从 SQLite 读数据 + 计算技术指标 + 组装 prompt |
| `server/services/action_registry.py` | **Action 注册表**（唯一真相源） |
| `server/services/action_handler.py` | Action 通用执行器（从注册表查找 handler） |
| `server/services/handlers/set_tp_sl.py` | 止盈止损 handler |
| `server/services/handlers/set_support_resistance.py` | 压力支撑位 handler |
| `server/services/handlers/add_watchlist.py` | 加入自选股 handler |
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
| `web/src/components/ai-chat/ActionCard.tsx` | Action 卡片容器（注册表路由） |
| `web/src/components/ai-chat/SimpleMarkdown.tsx` | Markdown 渲染组件 |
| `web/src/components/ai-chat/actions/registry.ts` | **前端 Action 注册表**（卡片 + 画线规则） |
| `web/src/components/ai-chat/actions/SetTpSlCard.tsx` | 止盈止损卡片组件 |
| `web/src/components/ai-chat/actions/SupportResistanceCard.tsx` | 压力支撑位卡片组件 |
| `web/src/components/ai-chat/actions/AddWatchlistCard.tsx` | 加入自选股卡片组件 |
| `web/src/components/ai-chat/actions/DefaultCard.tsx` | 未注册 Action 兜底卡片 |
| `web/src/pages/MarketPage.tsx` | 集成 AI 浮动按钮 + 画线联动（通用注册表） |
| `web/src/components/stock/StockDetailPanel.tsx` | 传递 extraMarkLines |
| `web/src/components/charts/KlineChart.tsx` | 支持 extraMarkLines 画标记线 |

## 五、Action 注册表模式（核心设计）

### 5.1 设计理念

采用**组件注册表（Component Registry）模式**，前后端各维护一个注册表作为唯一真相源。每个 Action = 一个 handler 文件 + 一行注册。

**好处：**
- 新增 Action 无需改动任何现有代码（ActionCard、MarketPage、prompt_builder 全部自动适配）
- 卡片样式一种一个组件，互不干扰
- 画线规则集中定义，前后端一致

### 5.2 后端注册表 (`server/services/action_registry.py`)

```python
REGISTRY = {
    "set_tp_sl": {
        "label": "设置止盈止损",
        "prompt_hint": '<action type="set_tp_sl" data=\'{"stock_code":"600519",...}\' />...',
        "handler": handle_set_tp_sl,        # handlers/set_tp_sl.py
        "chart_lines": [                     # K线图画线规则
            {"field": "tp_price",   "label": "止盈", "color": "rise",   "style": "dashed"},
            {"field": "sl_price",   "label": "止损", "color": "fall",   "style": "dashed"},
            {"field": "cost_price", "label": "成本", "color": "accent", "style": "solid"},
        ],
    },
    "set_support_resistance": {
        "label": "设置压力支撑位",
        "prompt_hint": '...',
        "handler": handle_support_resistance,  # handlers/set_support_resistance.py
        "chart_lines": [
            {"field": "pressure_price", "label": "压力位", "color": "rise", "style": "dotted"},
            {"field": "support_price",  "label": "支撑位", "color": "fall", "style": "dotted"},
        ],
    },
    "add_watchlist": {
        "label": "加入自选股",
        "prompt_hint": '...',
        "handler": handle_add_watchlist,
        "chart_lines": [],
    },
}
```

**自动能力：**
- `get_all_prompt_hints()` → prompt_builder 自动提取所有 action 说明
- `get_chart_lines(action_type)` → action 执行后返回画线规则
- `list_action_types()` → 列出所有已注册类型

### 5.3 前端注册表 (`web/src/components/ai-chat/actions/registry.ts`)

```typescript
export const ACTION_REGISTRY: Record<string, ActionRegistryEntry> = {
  set_tp_sl: {
    card: SetTpSlCard,           // 卡片组件
    chartLines: [                // 画线规则（与后端对应）
      { field: 'tp_price', label: '止盈', color: colors.rise, style: 'dashed' },
      { field: 'sl_price', label: '止损', color: colors.fall, style: 'dashed' },
      { field: 'cost_price', label: '成本', color: colors.accent, style: 'solid' },
    ],
  },
  // ...
}
```

**自动能力：**
- `getActionEntry(type)` → ActionCard 自动路由到对应卡片
- `buildMarkLines(type, data)` → MarketPage 自动生成 ECharts markLine
- 未注册类型 → 自动 fallback 到 DefaultCard

### 5.4 数据流

```
AI 回复 → 解析 <action/> → ActionCard(注册表路由卡片) → 确认 → POST /api/chat/actions
                                    │                                    │
                                    │  onActionExecuted 回调              ▼
                                    │                     action_handler.execute_action()
                                    ▼                              │
                          buildMarkLines(type, data)    注册表查找 handler → 写 DB
                                    │                              │
                                    ▼                              ▼
                    setExtraMarkLines([...])       返回 {chart_lines: [...]}
                                    │
                                    ▼
                         KlineChart 渲染标记线
```

## 六、数据流详解

### 6.1 聊天流程

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
      + 自动从 action_registry 提取可用 action 说明
   b. ai_client.stream_chat(system_prompt, messages) → 流式调 AI
   c. SSE 逐块返回 → data: {"type":"text","content":"..."}
5. 前端 useChatStream 逐块拼接 → 实时渲染 Markdown
6. AI 回复完成 → 解析 <action> 标签 → 渲染 ActionCard（通过注册表路由）
```

### 6.2 Action 执行流程

```
1. AI 回复末尾包含: <action type="set_tp_sl" data='{"tp_price":16.8,...}' />
2. 前端 parseActions() 从文本中提取 XML 标签
3. ActionCard 通过注册表找到对应卡片组件渲染
4. 用户点击"确认执行" → POST /api/chat/actions
5. 后端 action_handler:
   a. 从 REGISTRY 查找 handler
   b. 执行 handler（写 DB）
   c. 附加 chart_lines 规则返回
6. 前端 onActionExecuted 回调 → buildMarkLines(action.type, action.data)
7. MarketPage 更新 extraMarkLines 状态
8. KlineChart 渲染标记线（颜色/样式由注册表定义）
```

## 七、核心接口定义

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
  "message": "已保存止盈止损：止盈 120 / 止损 90",
  "data": {"id": 1, "code": "600519", "tp_price": 120, "sl_price": 90},
  "chart_lines": [
    {"field": "tp_price", "label": "止盈", "color": "rise", "style": "dashed"},
    {"field": "sl_price", "label": "止损", "color": "fall", "style": "dashed"},
    {"field": "cost_price", "label": "成本", "color": "accent", "style": "solid"}
  ]
}
```

## 八、数据库模型

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

### support_resistance 表（压力支撑位记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| code | VARCHAR(10) | 股票代码 |
| pressure_price | FLOAT | 压力位价格 |
| support_price | FLOAT | 支撑位价格 |
| reason | TEXT | AI 分析理由 |
| status | VARCHAR(10) | active / triggered / cancelled |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

## 九、Prompt 设计

系统提示词由 `prompt_builder.py` 动态组装，包含以下结构化数据：

```
【当前行情】最新价、涨跌幅、开盘、最高、最低、成交量、成交额
【技术面】MA5/MA10/MA20、RSI(6)、MACD(DIF/DEA/柱)、布林带(上/中/下轨)
【基本面】报告期、营业总收入、净利润、每股收益
【近10日走势摘要】涨跌天数、区间振幅、逐日涨跌幅
【用户持仓】（如提供）成本价、持仓数量、浮动盈亏

+ Action 列表（从 action_registry 自动提取，无需手动维护）
```

技术指标在后端实时计算（MA/RSI/MACD/布林带），数据来源于 SQLite 的 `stock_daily` 表。

## 十、Action 扩展指南

### 新增一个 Action 的步骤（4 步）

以新增"设置价格预警"为例：

**1. 后端 handler（新建 `server/services/handlers/set_alert.py`）**

```python
"""价格预警 handler"""
from a_stock_db.database import db

async def handle(data: dict) -> dict:
    code = data.get("stock_code")
    target = data.get("target_price")
    if not code or target is None:
        return {"success": False, "message": "缺少参数"}
    # 保存到数据库...
    return {"success": True, "message": f"预警已设置: {target}"}
```

**2. 后端注册（`server/services/action_registry.py` 加一项）**

```python
from server.services.handlers.set_alert import handle as handle_set_alert

REGISTRY = {
    # ... 已有 action ...
    "set_alert": {
        "label": "设置价格预警",
        "prompt_hint": (
            '<action type="set_alert" data=\'{"stock_code":"600519","target_price":150,'
            '"direction":"up","reason":"突破前高"}\' />\n'
            "要求: target_price 为纯数字"
        ),
        "handler": handle_set_alert,
        "chart_lines": [
            {"field": "target_price", "label": "预警", "color": "accent", "style": "dotted"},
        ],
    },
}
```

**3. 前端卡片（新建 `web/src/components/ai-chat/actions/SetAlertCard.tsx`）**

```tsx
export default function SetAlertCard({ data }: { data: Record<string, any> }) {
  return (
    <div>
      <div>预警价格: {data.target_price}</div>
      <div>方向: {data.direction === 'up' ? '向上突破' : '向下跌破'}</div>
    </div>
  )
}
```

**4. 前端注册（`web/src/components/ai-chat/actions/registry.ts` 加一项）**

```typescript
import SetAlertCard from './SetAlertCard'

export const ACTION_REGISTRY = {
  // ... 已有 action ...
  set_alert: {
    card: SetAlertCard,
    chartLines: [
      { field: 'target_price', label: '预警', color: colors.accent, style: 'dotted' },
    ],
  },
}
```

**完成！** 无需修改 ActionCard.tsx、MarketPage.tsx、prompt_builder.py、action_handler.py 中的任何代码。

如需数据库表，在 `server/db/models.py` 中添加即可。

### 自动适配的模块

| 模块 | 如何自动适配 |
|------|-------------|
| `prompt_builder.py` | 调用 `get_all_prompt_hints()` 自动提取 |
| `action_handler.py` | 从 REGISTRY 查找 handler 执行 |
| `ActionCard.tsx` | 通过 `getActionEntry()` 自动路由卡片组件 |
| `MarketPage.tsx` | 通过 `buildMarkLines()` 自动生成标记线 |
| 未注册类型 | 前端自动 fallback 到 DefaultCard |

## 十一、配置说明

### 环境变量（可选覆盖默认值）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| AI_API_KEY | 已预配置 | AI 服务 API Key |
| AI_BASE_URL | `https://aicoding-proxy.myunke.com/cn-cch` | AI 代理地址 |
| AI_MODEL | `glm-5` | 模型名称 |
| AI_TIMEOUT | `60` | 请求超时（秒） |

默认值已写在 `server/config.py` 中，无需额外配置即可使用。

## 十二、使用方式

1. 启动后端：`python -m server.run`
2. 启动前端：`cd web && npm run dev`
3. 打开行情页面，右下角出现 **AI** 浮动按钮
4. 点击打开聊天面板，输入问题
5. AI 分析后如给出操作建议（止盈止损/压力支撑位等），点击"确认执行"
6. K 线图自动标注对应标记线（颜色/样式由注册表定义）
