/** 基金净值折线图 — 基于 ECharts */
import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import * as echarts from 'echarts'
import type { FundNavPoint } from '../../api/fund'
import { colors, fonts } from '../../theme/tokens'

interface Props {
  data: FundNavPoint[]
  height?: number
}

export default function FundNavChart({ data, height = 400 }: Props) {
  const option = useMemo(() => {
    if (!data || data.length === 0) return {}

    const dates = data.map(d => d.date)
    const navs = data.map(d => d.nav)

    // 5 日 / 10 日均线
    const ma = (arr: number[], n: number) =>
      arr.map((_, i) => i < n - 1 ? null : arr.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0) / n)
    const ma5 = ma(navs, 5)
    const ma10 = ma(navs, 10)

    // 首尾对比决定颜色：涨红跌绿
    const first = navs[0]
    const last = navs[navs.length - 1]
    const isUp = last >= first
    const lineColor = isUp ? colors.rise : colors.fall
    const areaColorTop = isUp ? 'rgba(224,102,102,0.25)' : 'rgba(92,184,92,0.25)'
    const areaColorBottom = 'rgba(0,0,0,0)'

    return {
      backgroundColor: colors.bgSecondary,
      animation: true,
      animationDuration: 600,
      tooltip: {
        trigger: 'axis' as const,
        backgroundColor: '#1a1a1a',
        borderColor: colors.border,
        textStyle: {
          color: colors.textPrimary,
          fontFamily: fonts.mono,
          fontSize: 12,
        },
        formatter: (params: any) => {
          const p = params[0]
          const idx = p.dataIndex
          const point = data[idx]
          const pctStr = point.pct_change != null
            ? `<span style="color:${point.pct_change >= 0 ? colors.rise : colors.fall}">`
              + `${point.pct_change >= 0 ? '+' : ''}${point.pct_change.toFixed(2)}%</span>`
            : '-'
          return `<div style="font-family:${fonts.mono}">
            <div style="color:${colors.textMuted};font-size:11px;margin-bottom:4px">${p.axisValue}</div>
            <div>净值: <b>${point.nav.toFixed(4)}</b></div>
            <div>日增长率: ${pctStr}</div>
          </div>`
        },
      },
      grid: { left: 60, right: 20, top: 30, bottom: 30 },
      legend: { data: ['净值', 'MA5', 'MA10'], textStyle: { color: colors.textMuted, fontFamily: fonts.mono, fontSize: 10 }, top: 4 },
      xAxis: {
        type: 'category' as const,
        data: dates,
        axisLine: { lineStyle: { color: colors.border } },
        axisTick: { show: false },
        axisLabel: {
          color: colors.textMuted,
          fontSize: 10,
          fontFamily: fonts.mono,
          formatter: (v: string) => v.slice(5), // MM-DD
        },
      },
      yAxis: {
        type: 'value' as const,
        scale: true,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: colors.border, type: 'dashed' as const } },
        axisLabel: {
          color: colors.textMuted,
          fontSize: 10,
          fontFamily: fonts.mono,
          formatter: (v: number) => v.toFixed(4),
        },
      },
      dataZoom: [{ type: 'inside' as const, start: 0, end: 100 }],
      series: [{
        name: '净值',
        type: 'line',
        data: navs,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.5, color: lineColor },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: areaColorTop },
            { offset: 1, color: areaColorBottom },
          ]),
        },
      }, {
        name: 'MA5',
        type: 'line',
        data: ma5,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#f5a623' },
      }, {
        name: 'MA10',
        type: 'line',
        data: ma10,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#bd93f9' },
      }],
    }
  }, [data])

  if (!data || data.length === 0) {
    return (
      <div style={{
        height, display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: colors.textMuted, fontFamily: fonts.mono, fontSize: 13,
        background: colors.bgSecondary, borderRadius: 8,
      }}>
        暂无数据
      </div>
    )
  }

  return <ReactECharts option={option} style={{ height }} notMerge />
}
