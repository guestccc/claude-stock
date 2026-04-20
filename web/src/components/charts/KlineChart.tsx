/** K 线图组件 — 插件式架构 */
import { useMemo, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { DailyBar } from '../../api/market';
import {
  computeIndicators,
  toOHLC,
  type Indicators,
} from './indicators';
import {
  buildOverlays,
  overlayToSeries,
  overlayToLegend,
  type OverlayDef,
} from './overlays';
import { marks, marksToMarkPoint } from './marks';
import {
  subCharts,
  allSubTypes,
  buildSubSeries,
  type SubType,
} from './subcharts';

// ---------- 常量 ----------
const CHART_HEIGHT = 680;
const SUB_H = 80;
const SUB_GAP = 8;
const GAP = 18;
const TOP_PAD = 8;
const BOTTOM_PAD = 32;

const UP_COLOR = '#e06666';
const DOWN_COLOR = '#5cb85c';

// ---------- Props ----------
interface Props {
  data: DailyBar[];
  height?: number;
}

// ---------- 主组件 ----------
export default function KlineChart({ data, height = CHART_HEIGHT }: Props) {
  const [activeSubs, setActiveSubs] = useState<SubType[]>(['VOL', 'MACD', 'KDJ']);

  // ---------- 计算层（全部 useMemo） ----------
  const ohlc = useMemo(() => toOHLC(data), [data]);

  const needMACD = activeSubs.includes('MACD');
  const needKDJ = activeSubs.includes('KDJ');
  const ind: Indicators = useMemo(
    () => computeIndicators(data, needMACD, needKDJ),
    [data, needMACD, needKDJ],
  );

  const overlays: OverlayDef[] = useMemo(
    () => buildOverlays(ohlc, ind.donchian, ind.boll),
    [ohlc, ind.donchian, ind.boll],
  );

  const overlaySeries = useMemo(
    () => overlayToSeries(overlays),
    [overlays],
  );

  const legendData = useMemo(
    () => [
      { name: 'K线', icon: 'roundRect' },
      ...overlayToLegend(overlays),
    ],
    [overlays],
  );

  const klineMarkPoint = useMemo(
    () => marksToMarkPoint(marks, ohlc, overlays),
    [ohlc, overlays],
  );

  // ---------- 布局计算 ----------
  const subCount = activeSubs.length;
  const subAreaH = subCount * SUB_H + (subCount - 1) * SUB_GAP;
  const mainH = height - subAreaH - GAP - BOTTOM_PAD;
  const dates = ohlc.map((d) => d.date);

  // ---------- 图表组装 ----------
  const grid: object[] = [];
  const xAxis: object[] = [];
  const yAxis: object[] = [];
  const xAxisIdx: number[] = [0];

  // 主图
  grid.push({ left: 60, right: 20, top: TOP_PAD, height: mainH });
  xAxis.push({
    type: 'category',
    data: dates,
    gridIndex: 0,
    axisLine: { lineStyle: { color: '#1a1a1a' } },
    axisLabel: { color: '#6b7280', fontSize: 10 },
    splitLine: { show: false },
  });
  yAxis.push({
    type: 'value',
    scale: true,
    gridIndex: 0,
    splitLine: { lineStyle: { color: '#1a1a1a' } },
    axisLabel: { color: '#6b7280', fontSize: 10 },
    splitArea: { show: false },
  });

  // 副图 grid/xAxis/yAxis
  activeSubs.forEach((sub, idx) => {
    const gIdx = idx + 1;
    const top = TOP_PAD + mainH + GAP + idx * (SUB_H + SUB_GAP);
    grid.push({ left: 60, right: 20, top, height: SUB_H });
    xAxis.push({
      type: 'category',
      data: dates,
      gridIndex: gIdx,
      axisLabel: { show: false },
      axisLine: { lineStyle: { color: '#1a1a1a' } },
      splitLine: { show: false },
    });
    yAxis.push({
      type: 'value',
      scale: true,
      gridIndex: gIdx,
      splitLine: { show: false },
      axisLabel: { show: false },
    });
    xAxisIdx.push(gIdx);
  });

  // K 线 series
  const klineSeries = {
    name: 'K线',
    type: 'candlestick' as const,
    data: ohlc.map((d) => ({
      value: [d.open, d.close, d.low, d.high],
      pctChange: d.pctChange,
    })),
    xAxisIndex: 0,
    yAxisIndex: 0,
    itemStyle: {
      color: UP_COLOR,
      color0: DOWN_COLOR,
      borderColor: UP_COLOR,
      borderColor0: DOWN_COLOR,
    },
    markPoint:
      klineMarkPoint.length > 0
        ? {
            symbol: 'pin',
            symbolSize: 40,
            label: { color: '#fff', fontSize: 9, fontWeight: 'bold' as const },
            data: klineMarkPoint,
          }
        : undefined,
  };

  // 副图 series（xAxisIndex/yAxisIndex 在 buildSubSeries 中重映射到 1/2/3...）
  const subSeries = buildSubSeries(activeSubs, ohlc, ind, 1);

  const option: EChartsOption = {
    backgroundColor: '#2d2d2d',
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: '#1a1a1a',
      borderColor: '#2d2d2d',
      textStyle: { color: '#c4c9d4', fontSize: 11, fontFamily: 'monospace' },
      formatter(params: any[]) {
        if (!params.length) return '';
        const date = params[0].axisValue;
        let html = `<div style="margin-bottom:4px;color:#888">${date}</div>`;
        for (const p of params) {
          const { seriesName, data, marker } = p;
          let label = seriesName;
          let val = data;

          // K线：开高低收 + 涨幅（使用 API 返回的 pct_change）
          // ECharts axis trigger 下 value 格式为 [x, open, close, low, high]
          if (seriesName === 'K线') {
            const obj = data as { value: number[]; pctChange: number | null };
            const [, open, close, low, high] = obj.value;
            const chg = obj.pctChange != null ? obj.pctChange.toFixed(2) : '-';
            val = `开 ${open?.toFixed(2)}  高 ${high?.toFixed(2)}  低 ${low?.toFixed(2)}  收 ${close?.toFixed(2)}  涨幅 ${chg}%`;
          }
          // 唐奇安通道 / 布林带：从 data._lineType 取轨类型
          else if (
            seriesName === '唐奇安通道' ||
            seriesName === '布林带'
          ) {
            const obj = data as { value: number; _lineType: string } | string;
            if (obj !== '-') {
              const o = obj as { value: number; _lineType: string };
              label = `${seriesName}${o._lineType}`;
              val = o.value.toFixed(2);
            } else {
              val = '-';
            }
          }
          // 其他
          else if (typeof data === 'number') {
            val = data.toFixed(2);
          }

          html += `<div style="margin:2px 0">${marker} ${label}: <b>${val}</b></div>`;
        }
        return html;
      },
    },
    legend: {
      top: 10,
      right: 40,
      data: legendData,
      inactiveColor: '#3a3a3a',
      textStyle: { color: '#7a8099', fontSize: 10 },
      itemWidth: 14,
      itemHeight: 8,
    },
    graphic: buildSubLabels(activeSubs, subCount, mainH),
    grid,
    xAxis,
    yAxis,
    dataZoom: [{ type: 'inside', xAxisIndex: xAxisIdx, start: 70, end: 100 }],
    series: [klineSeries, ...overlaySeries, ...subSeries],
  };

  if (data.length === 0) {
    return (
      <div
        style={{
          width: '100%',
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#7a8099',
        }}
      >
        暂无数据
      </div>
    );
  }

  return (
    <div style={{ height }}>
      <SubToggle activeSubs={activeSubs} onToggle={setActiveSubs} />
      <ReactECharts
        option={option}
        style={{ width: '100%', height: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge={true}
      />
    </div>
  );
}

// ---------- 副图切换按钮 ----------
function SubToggle({
  activeSubs,
  onToggle,
}: {
  activeSubs: SubType[];
  onToggle: (next: SubType[]) => void;
}) {
  const toggle = (sub: SubType) => {
    onToggle((prev) => {
      if (prev.includes(sub)) return prev.length === 1 ? prev : prev.filter((s) => s !== sub);
      return [...prev, sub];
    });
  };

  return (
    <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
      {allSubTypes.map((sub) => {
        const def = subCharts.find((s) => s.id === sub)!;
        const active = activeSubs.includes(sub);
        return (
          <button
            key={sub}
            onClick={() => toggle(sub)}
            style={{
              padding: '2px 10px',
              fontSize: 10,
              border: '1px solid',
              borderColor: active ? def.color : '#3a3a3a',
              borderRadius: 4,
              background: active ? '#1a1a1a' : 'transparent',
              color: active ? def.color : '#3a3a3a',
              cursor: 'pointer',
            }}
          >
            {def.label}
          </button>
        );
      })}
    </div>
  );
}

// ---------- 副图标签（graphic） ----------
function buildSubLabels(
  activeSubs: SubType[],
  subCount: number,
  mainH: number,
): object[] {
  return activeSubs.map((sub, idx) => {
    const def = subCharts.find((s) => s.id === sub)!;
    const top = TOP_PAD + mainH + GAP + idx * (SUB_H + SUB_GAP) + 4;
    return {
      type: 'text',
      left: 62,
      top,
      style: {
        text: def.label,
        fill: def.color,
        fontSize: 10,
        fontFamily: 'JetBrains Mono, monospace',
      },
      z: 10,
      silent: true,
    };
  });
}
