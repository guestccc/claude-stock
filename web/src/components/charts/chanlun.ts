/**
 * 缠论计算引擎 — 纯函数，无副作用，无 React 依赖
 *
 * 计算管线：原始K线 → 包含处理 → 分型识别 → 笔 → 中枢 → 买卖点
 *
 * 渲染桥接：chanlunToOverlays / chanlunToMarkPoints / chanlunToPivotAreas
 * 供 KlineChart.tsx 调用，输出兼容现有 overlay / marks 架构的数据格式
 */
import type { OHLCData } from './indicators'

// ============================================================
// 类型定义
// ============================================================

/** 包含处理后的合并K线 */
export interface MergedBar {
  /** 合并后的高 */
  high: number
  /** 合并后的低 */
  low: number
  /** 参与合并的原始K线索引列表（用于坐标映射） */
  indices: number[]
}

/** 分型 */
export interface Fractal {
  /** 顶分型 or 底分型 */
  type: 'top' | 'bottom'
  /** 分型所在的合并K线索引 */
  mergedIdx: number
  /** 分型价格（顶=high，底=low） */
  value: number
  /** 映射到原始K线索引（取合并组中间位置，用于坐标定位） */
  barIndex: number
}

/** 笔 */
export interface Stroke {
  /** 起始分型 */
  from: Fractal
  /** 终止分型 */
  to: Fractal
  /** 笔内包含的合并K线数量（含端点） */
  mergedCount: number
}

/** 中枢 */
export interface Pivot {
  /** 中枢上沿（ZG）= min(各笔高点) */
  zg: number
  /** 中枢下沿（ZD）= max(各笔低点) */
  zd: number
  /** 起始原始K线索引 */
  startIdx: number
  /** 结束原始K线索引 */
  endIdx: number
  /** 构成中枢的笔序列 */
  strokes: Stroke[]
}

/** 买卖信号 */
export interface Signal {
  type: 'buy1' | 'buy2' | 'buy3' | 'sell1' | 'sell2' | 'sell3'
  barIndex: number
  price: number
  label: string
}

/** 缠论计算总结果 */
export interface ChanlunResult {
  merged: MergedBar[]
  fractals: Fractal[]
  strokes: Stroke[]
  pivots: Pivot[]
  signals: Signal[]
}

// ============================================================
// 1. 包含处理
// ============================================================

/**
 * 判断两根K线是否存在包含关系
 * 包含：一根K线的 [high, low] 完全包含另一根
 */
function hasInclusion(a: { high: number; low: number }, b: { high: number; low: number }): boolean {
  return (a.high >= b.high && a.low <= b.low) ||
         (b.high >= a.high && b.low <= a.low)
}

/**
 * 包含处理 — 合并相邻有包含关系的K线
 * 上升趋势：取高高（保留更高的高和更高的低）
 * 下降趋势：取低低（保留更低的高和更低的低）
 */
export function mergeInclusion(ohlc: OHLCData[]): MergedBar[] {
  if (ohlc.length === 0) return []

  const result: MergedBar[] = [{ high: ohlc[0].high, low: ohlc[0].low, indices: [0] }]

  for (let i = 1; i < ohlc.length; i++) {
    const cur = { high: ohlc[i].high, low: ohlc[i].low }
    const prev = result[result.length - 1]

    if (hasInclusion(prev, cur)) {
      // 判断趋势方向：与前一根（result 倒数第二根）比较
      let trend: 'up' | 'down' | 'none' = 'none'
      if (result.length >= 2) {
        const prevPrev = result[result.length - 2]
        trend = prev.high > prevPrev.high ? 'up' : 'down'
      }

      // 合并
      if (trend === 'up') {
        // 上升趋势：取高高
        prev.high = Math.max(prev.high, cur.high)
        prev.low = Math.max(prev.low, cur.low)
      } else {
        // 下降趋势或无趋势：取低低
        prev.high = Math.min(prev.high, cur.high)
        prev.low = Math.min(prev.low, cur.low)
      }
      prev.indices.push(i)
    } else {
      result.push({ high: cur.high, low: cur.low, indices: [i] })
    }
  }

  return result
}

// ============================================================
// 2. 分型识别
// ============================================================

/**
 * 在合并K线中识别分型
 * 顶分型：中间K线的高最高、低也最高
 * 底分型：中间K线的低最低、高也最低
 */
export function detectFractals(merged: MergedBar[]): Fractal[] {
  const fractals: Fractal[] = []
  if (merged.length < 3) return fractals

  for (let i = 1; i < merged.length - 1; i++) {
    const prev = merged[i - 1]
    const curr = merged[i]
    const next = merged[i + 1]

    // 顶分型：curr.high > prev.high && curr.high > next.high
    if (curr.high > prev.high && curr.high > next.high &&
        curr.low > prev.low && curr.low > next.low) {
      fractals.push({
        type: 'top',
        mergedIdx: i,
        value: curr.high,
        barIndex: curr.indices[Math.floor(curr.indices.length / 2)],
      })
    }
    // 底分型：curr.low < prev.low && curr.low < next.low
    else if (curr.low < prev.low && curr.low < next.low &&
             curr.high < prev.high && curr.high < next.high) {
      fractals.push({
        type: 'bottom',
        mergedIdx: i,
        value: curr.low,
        barIndex: curr.indices[Math.floor(curr.indices.length / 2)],
      })
    }
  }

  return fractals
}

// ============================================================
// 3. 笔识别
// ============================================================

/**
 * 从分型序列中识别笔
 * 规则：
 * 1. 笔连接相邻的顶底分型（必须交替）
 * 2. 顶底之间至少间隔 4 根合并K线（含端点共5根）
 * 3. 连续同向分型取极值
 */
/**
 * 从分型序列中识别笔
 *
 * 缠论标准：
 * 1. 笔连接相邻的顶底分型（严格交替：顶→底→顶→底...）
 * 2. 顶底之间至少间隔 4 根合并K线（gap >= 4）
 * 3. 连续同向分型取极值（顶取最高，底取最低）
 * 4. 上升笔：底→顶，顶值 > 底值；下降笔：顶→底，底值 < 顶值
 *
 * 算法（贪心扫描 + 价格验证 + 智能回退）：
 * 从 pending 分型出发，逐个检查后续异向分型：
 * - gap >= 4 且价格合理 → 成笔
 * - gap >= 4 但价格不合理 → pending 被"架空"，回退到 cur
 * - gap < 4 → 跳过 cur，保持 pending 不变
 */
export function detectStrokes(merged: MergedBar[], fractals: Fractal[]): Stroke[] {
  if (fractals.length < 2) return []

  // 第一步：合并连续同向分型，只保留极值
  const cleaned: Fractal[] = [fractals[0]]
  for (let i = 1; i < fractals.length; i++) {
    const last = cleaned[cleaned.length - 1]
    const cur = fractals[i]
    if (cur.type === last.type) {
      if ((cur.type === 'top' && cur.value > last.value) ||
          (cur.type === 'bottom' && cur.value < last.value)) {
        cleaned[cleaned.length - 1] = cur
      }
    } else {
      cleaned.push(cur)
    }
  }

  if (cleaned.length < 2) return []

  // 第二步：贪心连笔
  const MIN_GAP = 4
  const strokes: Stroke[] = []
  let pending = cleaned[0]

  for (let i = 1; i < cleaned.length; i++) {
    const cur = cleaned[i]

    // 同向分型：更新 pending 为更极端的
    if (cur.type === pending.type) {
      if ((cur.type === 'top' && cur.value > pending.value) ||
          (cur.type === 'bottom' && cur.value < pending.value)) {
        pending = cur
      }
      continue
    }

    // 异向分型
    const gap = Math.abs(cur.mergedIdx - pending.mergedIdx)

    if (gap >= MIN_GAP) {
      const priceOk = pending.type === 'top'
        ? pending.value > cur.value
        : cur.value > pending.value

      if (priceOk) {
        strokes.push({ from: pending, to: cur, mergedCount: gap + 1 })
        pending = cur
      } else {
        pending = cur
      }
    }
  }

  // 第三步：后处理 — 确保笔连续
  // 如果笔 i 的终点无法连接到笔 i+1 的起点（中间有断档），
  // 尝试延伸笔 i 的终点到笔 i+1 的起点
  for (let i = 0; i < strokes.length - 1; i++) {
    const cur = strokes[i]
    const next = strokes[i + 1]

    // 已连续
    if (cur.to.mergedIdx === next.from.mergedIdx) continue

    // 同类型才能延伸（top→top 或 bottom→bottom）
    if (cur.to.type !== next.from.type) continue

    // 检查延伸后是否仍满足 gap 和价格约束
    const newGap = Math.abs(next.from.mergedIdx - cur.from.mergedIdx)
    const newPriceOk = cur.from.type === 'top'
      ? cur.from.value > next.from.value
      : next.from.value > cur.from.value

    if (newGap >= MIN_GAP && newPriceOk) {
      strokes[i] = { from: cur.from, to: next.from, mergedCount: newGap + 1 }
    }
  }

  return strokes
}

// ============================================================
// 4. 中枢识别
// ============================================================

/**
 * 从笔序列中识别中枢
 *
 * 缠论中枢定义（简化版）：
 * - 至少 3 笔连续走势的价格重叠区域构成中枢
 * - ZG = min(各笔高点)：上沿
 * - ZD = max(各笔低点)：下沿
 * - 起点：第1笔的终点（即"进入笔"结束、中枢开始）
 * - 终点：最后一笔在中枢内的终点
 * - 后续笔仍在中枢区间内 [ZD, ZG] 振荡时，中枢延伸；脱离则结束
 */
export function detectPivots(_merged: MergedBar[], strokes: Stroke[]): Pivot[] {
  if (strokes.length < 3) return []

  const pivots: Pivot[] = []
  let i = 0

  while (i <= strokes.length - 3) {
    const s1 = strokes[i], s2 = strokes[i + 1], s3 = strokes[i + 2]

    // 三笔的高低
    const highs = [s1, s2, s3].map(s => Math.max(s.from.value, s.to.value))
    const lows = [s1, s2, s3].map(s => Math.min(s.from.value, s.to.value))

    const zg = Math.min(...highs)
    const zd = Math.max(...lows)

    // 有效中枢：必须有重叠区间
    if (zg > zd) {
      // 起点：第1笔的终点（"进入笔"结束的位置）
      const startIdx = s1.to.barIndex
      let endIdx = s3.to.barIndex
      let lastUsedStrokeIdx = i + 2
      const includedStrokes = [s1, s2, s3]

      // 向后延伸：后续笔仍在中枢区间内则延伸
      for (let j = i + 3; j < strokes.length; j++) {
        const nextStroke = strokes[j]
        const nextHigh = Math.max(nextStroke.from.value, nextStroke.to.value)
        const nextLow = Math.min(nextStroke.from.value, nextStroke.to.value)

        // 完全脱离中枢则结束
        if (nextHigh < zd || nextLow > zg) break

        endIdx = nextStroke.to.barIndex
        lastUsedStrokeIdx = j
        includedStrokes.push(nextStroke)
      }

      pivots.push({ zg, zd, startIdx, endIdx, strokes: includedStrokes })
      i = lastUsedStrokeIdx + 1
    } else {
      i++
    }
  }

  return pivots
}

// ============================================================
// 5. 买卖点识别
// ============================================================

/** 简单 MACD 计算（12/26/9），仅用于背驰判断，返回 histogram 数组 */
function simpleMACD(closes: number[]): number[] {
  if (closes.length < 26) return []

  const ema = (data: number[], period: number): number[] => {
    const k = 2 / (period + 1)
    const result: number[] = [data[0]]
    for (let i = 1; i < data.length; i++) {
      result.push(data[i] * k + result[i - 1] * (1 - k))
    }
    return result
  }

  const ema12 = ema(closes, 12)
  const ema26 = ema(closes, 26)
  const dif = ema12.map((v, i) => v - ema26[i])
  const dea = ema(dif, 9)
  return dif.map((v, i) => (v - dea[i]) * 2) // histogram = (DIF - DEA) * 2
}

/**
 * 背驰检测
 * 比较参考段（中枢内）和离开段的 MACD 柱面积 / 价格幅度
 * 离开段动量更弱 = 背驰（返回 true）
 */
function checkDivergence(
  histogram: number[],
  closes: number[],
  refStart: number, refEnd: number,
  leaveStart: number, leaveEnd: number,
  direction: 'down' | 'up',
): boolean {
  const clamp = (idx: number) => Math.max(0, Math.min(idx, histogram.length - 1))
  const isDown = direction === 'down'

  // MACD 面积：只累加对应方向的柱
  let refArea = 0
  let leaveArea = 0
  if (histogram.length > 0) {
    for (let i = clamp(refStart); i <= clamp(refEnd); i++) {
      if (isDown ? histogram[i] < 0 : histogram[i] > 0) refArea += Math.abs(histogram[i])
    }
    for (let i = clamp(leaveStart); i <= clamp(leaveEnd); i++) {
      if (isDown ? histogram[i] < 0 : histogram[i] > 0) leaveArea += Math.abs(histogram[i])
    }
  }

  // 幅度比较
  const refAmp = Math.abs((closes[refEnd] ?? 0) - (closes[refStart] ?? 0))
  const leaveAmp = Math.abs((closes[leaveEnd] ?? 0) - (closes[leaveStart] ?? 0))

  // MACD 背驰 OR 幅度背驰（满足任一即可）
  if (histogram.length > 0 && (refArea > 0 || leaveArea > 0)) {
    return leaveArea < refArea || leaveAmp < refAmp
  }
  // 无 MACD 数据时仅用幅度
  return leaveAmp < refAmp
}

/**
 * 识别买卖信号（含背驰判断）
 *
 * 一买：跌破中枢 ZD 后回升 + 离开段与中枢内参考段形成背驰（动量衰减）
 * 二买：一买后回调不破一买低点，再次收阳确认
 * 三买：中枢内震荡后首次突破 ZG（之前未离开过中枢区间）
 *
 * 卖点对称。三买/三卖不需要背驰。
 */
export function detectSignals(
  ohlc: OHLCData[],
  merged: MergedBar[],
  pivots: Pivot[],
): Signal[] {
  const signals: Signal[] = []
  if (pivots.length === 0) return signals

  // 预计算 MACD（用于背驰判断）
  const closes = ohlc.map(d => d.close)
  const macdHist = simpleMACD(closes)

  for (const pivot of pivots) {
    const startScan = pivot.endIdx
    const endScan = Math.min(ohlc.length, startScan + 80)

    let belowPivot = false
    let abovePivot = false
    let buy1Found = false
    let sell1Found = false
    let buy1Price = 0
    let sell1Price = 0
    let buy1Idx = -1
    let sell1Idx = -1
    let buy2Found = false
    let sell2Found = false

    // 从中枢笔中找参考段（最后一根向下笔 = 一买参考，最后一根向上笔 = 一卖参考）
    let refDownStart = pivot.startIdx
    let refDownEnd = pivot.endIdx
    let refUpStart = pivot.startIdx
    let refUpEnd = pivot.endIdx
    for (let si = pivot.strokes.length - 1; si >= 0; si--) {
      const s = pivot.strokes[si]
      if (s.from.value > s.to.value) {
        refDownStart = s.from.barIndex
        refDownEnd = s.to.barIndex
        break
      }
    }
    for (let si = pivot.strokes.length - 1; si >= 0; si--) {
      const s = pivot.strokes[si]
      if (s.from.value < s.to.value) {
        refUpStart = s.from.barIndex
        refUpEnd = s.to.barIndex
        break
      }
    }

    for (let i = startScan; i < endScan; i++) {
      const bar = ohlc[i]
      if (!bar) break

      // === 三买/三卖（不需要背驰） ===
      if (!abovePivot && !belowPivot && bar.close > pivot.zg) {
        signals.push({ type: 'buy3', barIndex: i, price: bar.low, label: '三买' })
        abovePivot = true
        continue
      }
      if (!abovePivot && !belowPivot && bar.close < pivot.zd) {
        signals.push({ type: 'sell3', barIndex: i, price: bar.high, label: '三卖' })
        belowPivot = true
        continue
      }

      // === 更新脱离标记 ===
      if (bar.low < pivot.zd) belowPivot = true
      if (bar.high > pivot.zg) abovePivot = true

      // === 一买 + 背驰确认 ===
      if (belowPivot && !buy1Found && bar.close >= pivot.zd && bar.close <= pivot.zg) {
        const divergent = checkDivergence(
          macdHist, closes,
          refDownStart, refDownEnd,   // 参考段：中枢内最后一根向下笔
          startScan, i,                // 离开段：中枢结束后到当前
          'down',
        )
        if (divergent) {
          signals.push({ type: 'buy1', barIndex: i, price: bar.low, label: '一买' })
          buy1Found = true
          buy1Price = bar.low
          buy1Idx = i
        }
      }

      // === 二买：一买后回调不破一买低点，再次收阳确认 ===
      if (buy1Found && !buy2Found && i > buy1Idx + 1) {
        if (bar.close > bar.open && bar.low > buy1Price * 0.99) {
          let hadPullback = false
          let pullbackLow = Infinity
          for (let j = buy1Idx + 1; j < i; j++) {
            if (ohlc[j]) {
              pullbackLow = Math.min(pullbackLow, ohlc[j].low)
              if (ohlc[j].close < ohlc[j].open) hadPullback = true
            }
          }
          if (hadPullback && pullbackLow >= buy1Price * 0.99) {
            signals.push({ type: 'buy2', barIndex: i, price: bar.low, label: '二买' })
            buy2Found = true
          }
        }
      }

      // === 一卖 + 背驰确认 ===
      if (abovePivot && !sell1Found && bar.close <= pivot.zg && bar.close >= pivot.zd) {
        const divergent = checkDivergence(
          macdHist, closes,
          refUpStart, refUpEnd,
          startScan, i,
          'up',
        )
        if (divergent) {
          signals.push({ type: 'sell1', barIndex: i, price: bar.high, label: '一卖' })
          sell1Found = true
          sell1Price = bar.high
          sell1Idx = i
        }
      }

      // === 二卖：一卖后反弹不破一卖高点，再次收阴确认 ===
      if (sell1Found && !sell2Found && i > sell1Idx + 1) {
        if (bar.close < bar.open && bar.high < sell1Price * 1.01) {
          let hadBounce = false
          let bounceHigh = 0
          for (let j = sell1Idx + 1; j < i; j++) {
            if (ohlc[j]) {
              bounceHigh = Math.max(bounceHigh, ohlc[j].high)
              if (ohlc[j].close > ohlc[j].open) hadBounce = true
            }
          }
          if (hadBounce && bounceHigh <= sell1Price * 1.01) {
            signals.push({ type: 'sell2', barIndex: i, price: bar.high, label: '二卖' })
            sell2Found = true
          }
        }
      }
    }
  }

  return signals
}

// ============================================================
// 6. 主计算入口
// ============================================================

/** 缠论完整计算 */
export function computeChanlun(ohlc: OHLCData[]): ChanlunResult {
  const merged = mergeInclusion(ohlc)
  const fractals = detectFractals(merged)
  const strokes = detectStrokes(merged, fractals)
  const pivots = detectPivots(merged, strokes)
  const signals = detectSignals(ohlc, merged, pivots)

  // ===== DEBUG: 打印到控制台 =====
  console.group('[缠论 DEBUG]')
  console.log('原始K线:', ohlc.length, '条')
  console.log('合并K线:', merged.length, '条')
  console.log('分型:', fractals.length, '个')
  fractals.forEach((f, i) => {
    console.log(`  分型${i}: [${f.mergedIdx}]${f.type} val=${f.value} barIdx=${f.barIndex} date=${ohlc[f.barIndex]?.date}`)
  })
  console.log('笔:', strokes.length, '根')
  strokes.forEach((s, i) => {
    const dir = s.from.type === 'top' ? '↓下降' : '↑上升'
    console.log(`  笔${i + 1}: [${s.from.mergedIdx}]${s.from.type}(${s.from.value})@${ohlc[s.from.barIndex]?.date} → [${s.to.mergedIdx}]${s.to.type}(${s.to.value})@${ohlc[s.to.barIndex]?.date} ${dir} gap=${s.mergedCount - 1}`)
  })
  // 检查连续同向
  for (let i = 1; i < strokes.length; i++) {
    const prev = strokes[i - 1], cur = strokes[i]
    const prevDir = prev.from.type === 'top' ? 'DOWN' : 'UP'
    const curDir = cur.from.type === 'top' ? 'DOWN' : 'UP'
    if (prevDir === curDir) {
      console.warn(`  ⚠️ 连续同向! 笔${i}(↓)和笔${i + 1}(↓)`, prevDir)
    }
  }
  console.log('中枢:', pivots.length, '个')
  pivots.forEach((p, i) => {
    console.log(`  中枢${i + 1}: ZG=${p.zg.toFixed(2)} ZD=${p.zd.toFixed(2)} ${ohlc[p.startIdx]?.date}~${ohlc[p.endIdx]?.date}`)
  })
  console.log('信号:', signals.length, '个')
  signals.forEach((s, i) => {
    console.log(`  ${s.label}: bar=${s.barIndex}(${ohlc[s.barIndex]?.date}) price=${s.price}`)
  })
  console.groupEnd()
  // ===== END DEBUG =====

  return { merged, fractals, strokes, pivots, signals }
}

// ============================================================
// 7. 渲染桥接 — 输出兼容现有图表架构的数据
// ============================================================

/** markLine 的线段数据 */
export interface MarkLineDataItem {
  coord: [number, number]
}

/**
 * 将笔渲染为 markLine 线段数据
 * 每笔是从 from.barIndex → to.barIndex 的直线段
 */
export function chanlunToMarkLines(result: ChanlunResult): Array<[MarkLineDataItem, MarkLineDataItem]> {
  return result.strokes.map(s => [
    { coord: [s.from.barIndex, s.from.value] as [number, number] },
    { coord: [s.to.barIndex, s.to.value] as [number, number] },
  ])
}

/**
 * 将分型 + 买卖点渲染为 ECharts markPoint 数据
 */
export function chanlunToMarkPoints(result: ChanlunResult): any[] {
  const points: any[] = []

  // 分型标记
  for (const f of result.fractals) {
    if (f.type === 'top') {
      points.push({
        coord: [f.barIndex, f.value],
        symbol: 'triangle',
        symbolSize: 7,
        symbolRotate: 180,
        symbolOffset: [0, '-50%'],
        itemStyle: { color: '#e06666' },
        label: { show: false },
      })
    } else {
      points.push({
        coord: [f.barIndex, f.value],
        symbol: 'triangle',
        symbolSize: 7,
        symbolOffset: [0, '50%'],
        itemStyle: { color: '#5cb85c' },
        label: { show: false },
      })
    }
  }

  // 买卖信号标记
  for (const s of result.signals) {
    const isBuy = s.type.startsWith('buy')
    points.push({
      coord: [s.barIndex, s.price],
      symbol: 'circle',
      symbolSize: 10,
      symbolOffset: isBuy ? [0, '80%'] : [0, '-80%'],
      itemStyle: { color: isBuy ? '#e06666' : '#5cb85c' },
      label: {
        show: true,
        formatter: s.label,
        position: isBuy ? 'bottom' : 'top',
        fontSize: 10,
        color: isBuy ? '#e06666' : '#5cb85c',
      },
    })
  }

  return points
}

/** markArea 类型（避免直接 import echarts 的复杂类型） */
export interface PivotAreaItem {
  xAxis: number
  yAxis: number
  name?: string
}

/**
 * 将中枢渲染为 ECharts markArea 数据
 * 每个中枢是一个矩形 [startIdx~endIdx, ZD~ZG]，并标注 ZG/ZD 价格
 */
export function chanlunToPivotAreas(result: ChanlunResult): Array<[PivotAreaItem, PivotAreaItem]> {
  return result.pivots.map(p => [
    { xAxis: p.startIdx, yAxis: p.zg, name: `ZG=${p.zg.toFixed(2)}` },
    { xAxis: p.endIdx, yAxis: p.zd, name: `ZD=${p.zd.toFixed(2)}` },
  ])
}
