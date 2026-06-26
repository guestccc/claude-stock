/**
 * Action 前端注册表 — 与后端 action_registry.py 对应
 *
 * 新增 action 只需:
 *   1. 新建 XxxCard.tsx 组件
 *   2. 在此文件 REGISTRY 中加一项
 *   3. 对应后端 action_registry.py 也加一项
 */
import { colors } from '../../../theme/tokens'

/** 注册表条目 */
export interface ActionRegistryEntry {
  /** 卡片组件（懒加载 key 或直接组件） */
  card: React.ComponentType<{ data: Record<string, any> }>
  /** K 线图标记线规则（与后端 chart_lines 对应） */
  chartLines: ChartLineRule[]
}

/** K 线图画线规则 */
export interface ChartLineRule {
  /** action data 中的字段名 */
  field: string
  /** 线标签（如 "止盈"） */
  label: string
  /** 颜色 key，对应 tokens.ts 中的 colors key */
  color: string
  /** 线样式 */
  style: 'solid' | 'dashed' | 'dotted'
}

// 延迟导入卡片组件，避免循环依赖
import SetTpSlCard from './SetTpSlCard'
import SupportResistanceCard from './SupportResistanceCard'
import AddWatchlistCard from './AddWatchlistCard'
import DefaultCard from './DefaultCard'

/**
 * Action 注册表
 * chartLines 的 color/style 与后端 action_registry.py 保持一致
 */
export const ACTION_REGISTRY: Record<string, ActionRegistryEntry> = {
  set_tp_sl: {
    card: SetTpSlCard,
    chartLines: [
      { field: 'tp_price', label: '止盈', color: colors.rise, style: 'dashed' },
      { field: 'sl_price', label: '止损', color: colors.fall, style: 'dashed' },
      { field: 'cost_price', label: '成本', color: colors.accent, style: 'solid' },
    ],
  },
  set_support_resistance: {
    card: SupportResistanceCard,
    chartLines: [
      { field: 'pressure_price', label: '压力位', color: colors.rise, style: 'dotted' },
      { field: 'support_price', label: '支撑位', color: colors.fall, style: 'dotted' },
    ],
  },
  add_watchlist: {
    card: AddWatchlistCard,
    chartLines: [],
  },
}

/** 获取注册表条目，未注册的返回默认 */
export function getActionEntry(type: string): ActionRegistryEntry {
  return ACTION_REGISTRY[type] || { card: DefaultCard, chartLines: [] }
}

/** 根据 action 类型和 data 生成 ECharts markLine 数据 */
export function buildMarkLines(
  actionType: string,
  data: Record<string, any>,
): object[] {
  const entry = ACTION_REGISTRY[actionType]
  if (!entry) return []

  return entry.chartLines
    .filter((rule) => data[rule.field] != null)
    .map((rule) => ({
      yAxis: data[rule.field],
      label: { formatter: `${rule.label} ${data[rule.field]}`, color: rule.color, fontSize: 10 },
      lineStyle: { color: rule.color, width: 1, type: rule.style as 'solid' | 'dashed' | 'dotted' },
    }))
}
