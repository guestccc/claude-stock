/** K 线图组件 — 基于 ECharts */
import { useRef, useEffect } from 'react'
import * as echarts from 'echarts'
import type { DailyBar } from '../../api/market'

interface Props {
  data: DailyBar[]
  height?: number
}

export default function KlineChart({ data, height = 360 }: Props) {
  const chartRef = useRef<HTMLDivElement>(null)
  const instanceRef = useRef<echarts.ECharts>()

  useEffect(() => {
    if (!chartRef.current) return

    // 初始化或获取实例
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, 'dark')
    }

    const chart = instanceRef.current

    if (data.length === 0) return

    const dates = data.map((d) => d.date)
    const ohlc = data.map((d) => [d.open, d.close, d.low, d.high])
    const volumes = data.map((d) => d.volume ?? 0)
    // 成交量颜色：涨绿跌红（A股惯例）
    const volumeColors = data.map((d) =>
      d.close != null && d.open != null && d.close >= d.open ? '#5cb85c' : '#e06666'
    )

    const option: echarts.EChartsOption = {
      backgroundColor: '#2d2d2d',
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: '#1a1a1a',
        borderColor: '#2d2d2d',
        textStyle: { color: '#c4c9d4', fontSize: 12, fontFamily: 'monospace' },
      },
      grid: [
        { left: 60, right: 20, top: 20, height: '60%' },
        { left: 60, right: 20, top: '78%', height: '15%' },
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          axisLine: { lineStyle: { color: '#1a1a1a' } },
          axisLabel: { color: '#6b7280', fontSize: 10 },
          gridIndex: 0,
        },
        {
          type: 'category',
          data: dates,
          gridIndex: 1,
          axisLabel: { show: false },
          axisLine: { lineStyle: { color: '#1a1a1a' } },
        },
      ],
      yAxis: [
        {
          type: 'value',
          scale: true,
          splitLine: { lineStyle: { color: '#1a1a1a' } },
          axisLabel: { color: '#6b7280', fontSize: 10 },
          gridIndex: 0,
        },
        {
          type: 'value',
          scale: true,
          gridIndex: 1,
          splitLine: { show: false },
          axisLabel: { show: false },
        },
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 70,
          end: 100,
        },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: ohlc,
          xAxisIndex: 0,
          yAxisIndex: 0,
          itemStyle: {
            color: '#5cb85c',
            color0: '#e06666',
            borderColor: '#5cb85c',
            borderColor0: '#e06666',
          },
        },
        {
          name: '成交量',
          type: 'bar',
          data: volumes.map((v, i) => ({
            value: v,
            itemStyle: { color: volumeColors[i] },
          })),
          xAxisIndex: 1,
          yAxisIndex: 1,
        },
      ],
    }

    chart.setOption(option, true)

    // 响应式
    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [data])

  // 组件卸载销毁图表
  useEffect(() => {
    return () => {
      instanceRef.current?.dispose()
    }
  }, [])

  return <div ref={chartRef} style={{ width: '100%', height }} />
}
