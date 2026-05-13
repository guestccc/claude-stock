/** K 线图组件 — 插件式架构 */
import { useMemo, useState, useRef, useEffect, useCallback } from 'react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import type { MarkPointOption } from 'echarts';
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
import { marks, marksToMarkPoint, findMarkById } from './marks';
import {
  computeChanlun,
  chanlunToMarkLines,
  chanlunToMarkPoints,
  chanlunToPivotAreas,
} from './chanlun';
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
  onLoadMore?: () => void;
  isLoadingMore?: boolean;
  hasMore?: boolean;
  /** 额外标记点（如买卖点），直接合并到 K 线 series 的 markPoint */
  extraMarkPoints?: MarkPointOption[];
}

// ---------- 主组件 ----------
export default function KlineChart({ data, height = CHART_HEIGHT, onLoadMore, isLoadingMore, hasMore, extraMarkPoints }: Props) {
  const [activeSubs, setActiveSubs] = useState<SubType[]>(['VOL', 'MACD', 'KDJ']);
  const [chanlunActive, setChanlunActive] = useState(false);

  // ---------- 分页加载：refs ----------
  const chartRef = useRef<ReactECharts>(null);
  const cooldownRef = useRef(false);
  const isLoadingRef = useRef(false);
  const hasMoreRef = useRef(true);
  const onLoadMoreRef = useRef(onLoadMore);

  useEffect(() => { isLoadingRef.current = isLoadingMore ?? false; }, [isLoadingMore]);
  useEffect(() => { hasMoreRef.current = hasMore ?? true; }, [hasMore]);
  useEffect(() => { onLoadMoreRef.current = onLoadMore; }, [onLoadMore]);

  // ---------- 分页加载：通过 onEvents 绑定 dataZoom ----------
  const handleDataZoom = useCallback((params: any) => {
    if (!hasMoreRef.current || isLoadingRef.current || cooldownRef.current) return;
    const batch = params.batch || [];
    const isAtLeftEdge = batch.some((b: any) => b.start <= 2);
    if (isAtLeftEdge) {
      cooldownRef.current = true;
      onLoadMoreRef.current?.();
      setTimeout(() => { cooldownRef.current = false; }, 2000);
    }
  }, []);

  // ---------- 分页加载：数据 prepend 后调整 dataZoom 保持视图 ----------
  const dataLenRef = useRef(data.length);
  useEffect(() => {
    const delta = data.length - dataLenRef.current;
    dataLenRef.current = data.length;

    if (delta > 0 && dataLenRef.current > delta) {
      const chart = chartRef.current?.getEchartsInstance();
      if (!chart) return;
      const option = chart.getOption() as any;
      const dz = option.dataZoom?.[0];
      if (dz && dz.startValue != null) {
        setTimeout(() => {
          chart.dispatchAction({
            type: 'dataZoom',
            startValue: dz.startValue + delta,
            endValue: dz.endValue + delta,
          });
        }, 50);
      }
    }
  }, [data]);

  // ---------- 计算层（全部 useMemo） ----------
  const ohlc = useMemo(() => toOHLC(data), [data]);

  const needMACD = activeSubs.includes('MACD');
  const needKDJ = activeSubs.includes('KDJ');
  const ind: Indicators = useMemo(
    () => computeIndicators(data, needMACD, needKDJ),
    [data, needMACD, needKDJ],
  );

  const overlays: OverlayDef[] = useMemo(
    () => buildOverlays(ohlc, ind.donchian, ind.boll, ind.ma5, ind.ma10, ind.ma20),
    [ohlc, ind.donchian, ind.boll, ind.ma5, ind.ma10, ind.ma20],
  );

  const overlaySeries = useMemo(
    () => overlayToSeries(overlays),
    [overlays],
  );

  // 缠论计算（条件计算，关闭时不消耗性能）
  const chanlunResult = useMemo(
    () => chanlunActive ? computeChanlun(ohlc) : null,
    [ohlc, chanlunActive],
  );
  const chanlunMarkLines = useMemo(
    () => chanlunResult ? chanlunToMarkLines(chanlunResult) : [],
    [chanlunResult],
  );
  const chanlunMarkPoints = useMemo(
    () => chanlunResult ? chanlunToMarkPoints(chanlunResult) : [],
    [chanlunResult],
  );
  const chanlunPivotAreas = useMemo(
    () => chanlunResult ? chanlunToPivotAreas(chanlunResult) : [],
    [chanlunResult],
  );

  const legendData = useMemo(
    () => [
      { name: 'K线', icon: 'roundRect' },
      ...overlayToLegend(overlays),
      { name: '突破', icon: 'pin' },
      { name: '破位', icon: 'pin' },
    ],
    [overlays],
  );

  // 突破/破位标记点（独立于 klineMarkPoint，用于各自 series）
  const breakoutPoints = useMemo(
    () => {
      const m = findMarkById('breakout');
      const m2 = findMarkById('dc_breakout');
      const pts: any[] = [];
      if (m) pts.push(...m.detect(ohlc, overlays));
      if (m2) pts.push(...m2.detect(ohlc, overlays));
      return pts;
    },
    [ohlc, overlays],
  );
  const breakdownPoints = useMemo(
    () => findMarkById('breakdown')?.detect(ohlc, overlays) ?? [],
    [ohlc, overlays],
  );

  // klineMarkPoint 不再包含突破/破位（已拆到独立 series）
  const klineMarkPoint = useMemo(
    () => [],
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

  // 合并所有 markPoints（原有 + 缠论分型/买卖点）
  const allMarkPoints = useMemo(
    () => [...klineMarkPoint, ...(extraMarkPoints || []), ...chanlunMarkPoints],
    [klineMarkPoint, extraMarkPoints, chanlunMarkPoints],
  );

  // K 线 series
  const klineSeries = {
    id: 'kline',
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
      allMarkPoints.length > 0
        ? {
            symbol: 'pin',
            symbolSize: 40,
            label: { color: '#fff', fontSize: 9, fontWeight: 'bold' as const },
            data: allMarkPoints,
          }
        : undefined,
    // 缠论中枢矩形区域
    markArea: chanlunPivotAreas.length > 0
      ? {
          silent: true,
          itemStyle: { color: 'rgba(122, 164, 245, 0.12)', borderWidth: 1.5, borderColor: 'rgba(122, 164, 245, 0.5)', borderType: 'dashed' as const },
          label: { show: true, position: 'insideTopLeft', fontSize: 9, color: 'rgba(122, 164, 245, 0.7)', formatter: '中枢' },
          data: chanlunPivotAreas,
        }
      : undefined,
    // 缠论笔折线
    markLine: chanlunMarkLines.length > 0
      ? {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#f5a623', width: 1.5, type: 'solid' as const },
          label: { show: false },
          data: chanlunMarkLines,
        }
      : undefined,
  };

  // 副图 series（xAxisIndex/yAxisIndex 在 buildSubSeries 中重映射到 1/2/3...）
  const subSeries = buildSubSeries(activeSubs, ohlc, ind, 1);

  // 突破/破位独立 series（legend 可点击控制显隐）
  const markSeries = [
    {
      id: 'breakout-series',
      name: '突破',
      type: 'scatter' as const,
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: breakoutPoints,
      symbolSize: 0,
      markPoint: {
        symbol: 'pin',
        symbolSize: 28,
        symbolOffset: [0, -30],
        itemStyle: { opacity: 0.5 },
        label: { show: false },
        data: breakoutPoints,
      },
      tooltip: { show: false },
      z: 5,
    },
    {
      id: 'breakdown-series',
      name: '破位',
      type: 'scatter' as const,
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: breakdownPoints,
      symbolSize: 0,
      markPoint: {
        symbol: 'pin',
        symbolSize: 28,
        symbolOffset: [0, 30],
        itemStyle: { opacity: 0.5 },
        label: { show: false },
        data: breakdownPoints,
      },
      tooltip: { show: false },
      z: 5,
    },
  ];

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
          // 通道线 / 均线：从 data._lineType 取类型
          else if (
            seriesName === '唐奇安通道' ||
            seriesName === '布林带' ||
            seriesName === '均线'
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
      left: 'center',
      data: legendData,
      inactiveColor: '#3a3a3a',
      textStyle: { color: '#7a8099', fontSize: 10 },
      itemWidth: 14,
      itemHeight: 8,
      selected: {
        'K线': true,
        '唐奇安通道': false,
        '布林带': false,
        '均线': false,
        '突破': false,
        '破位': false,
      },
    },
    graphic: buildSubLabels(activeSubs, subCount, mainH),
    grid,
    xAxis,
    yAxis,
    dataZoom: [{ type: 'inside', xAxisIndex: xAxisIdx, start: 70, end: 100 }],
    series: [klineSeries, ...overlaySeries, ...markSeries, ...subSeries],
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
    <div style={{ height, position: 'relative' }}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 6, alignItems: 'center' }}>
        {allSubTypes.map((sub) => {
          const def = subCharts.find((s) => s.id === sub)!;
          const active = activeSubs.includes(sub);
          return (
            <button
              key={sub}
              onClick={() => {
                setActiveSubs((prev) => {
                  if (prev.includes(sub)) return prev.length === 1 ? prev : prev.filter((s) => s !== sub);
                  return [...prev, sub];
                });
              }}
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
        <span style={{ width: 1, height: 14, background: '#3a3a3a', margin: '0 4px' }} />
        <button
          onClick={() => setChanlunActive(!chanlunActive)}
          style={{
            padding: '2px 10px',
            fontSize: 10,
            border: '1px solid',
            borderColor: chanlunActive ? '#f5a623' : '#3a3a3a',
            borderRadius: 4,
            background: chanlunActive ? '#1a1a1a' : 'transparent',
            color: chanlunActive ? '#f5a623' : '#3a3a3a',
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >缠论</button>
      </div>
      {isLoadingMore && hasMore && (
        <div style={{ position: 'absolute', left: 60, top: 8, color: '#f5a742', fontSize: 11, zIndex: 10 }}>
          加载历史数据中...
        </div>
      )}
      {chanlunActive && <ChanlunLegend />}
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ width: '100%', height: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge={true}
        onEvents={{ dataZoom: handleDataZoom }}
      />
    </div>
  );
}

// ---------- 缠论固定图例栏 ----------
const CHANLUN_LEGEND = [
  { icon: '▲', color: '#5cb85c', label: '底分型', desc: '相邻3根合并K线中，中间那根低点最低' },
  { icon: '▼', color: '#e06666', label: '顶分型', desc: '相邻3根合并K线中，中间那根高点最高' },
  { icon: '━', color: '#f5a623', label: '笔', desc: '连接相邻顶底分型的折线段（至少5根K线）' },
  { icon: '▮', color: 'rgba(122,164,245,0.7)', label: '中枢', desc: '至少3笔的价格重叠区间[ZD,ZG]' },
  { icon: '①', color: '#e06666', label: '一买', desc: '跌破ZD后首次回升进入中枢' },
  { icon: '②', color: '#e06666', label: '二买', desc: '一买后回调不破一买低点再收阳' },
  { icon: '③', color: '#e06666', label: '三买', desc: '中枢内震荡后首次突破ZG' },
  { icon: '①', color: '#5cb85c', label: '一卖', desc: '突破ZG后首次回落进入中枢' },
  { icon: '②', color: '#5cb85c', label: '二卖', desc: '一卖后反弹不破一卖高点再收阴' },
  { icon: '③', color: '#5cb85c', label: '三卖', desc: '中枢内震荡后首次跌破ZD' },
]

function ChanlunLegend() {
  return (
    <div style={{
      display: 'flex',
      flexWrap: 'wrap',
      gap: '8px 16px',
      padding: '4px 8px',
      marginBottom: 4,
      background: 'rgba(26,26,26,0.6)',
      borderRadius: 4,
      border: '1px solid #2a2a2a',
    }}>
      {CHANLUN_LEGEND.map((item) => (
        <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ color: item.color, fontSize: 12, fontFamily: 'monospace', lineHeight: 1 }}>{item.icon}</span>
          <span style={{ color: item.color, fontSize: 10 }}>{item.label}</span>
          <span style={{ color: '#6b7280', fontSize: 9 }}>{item.desc}</span>
        </div>
      ))}
    </div>
  )
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
