/** 通道线注册表 — 可扩展的 Overlay 插件 */
import type { EChartsSeriesOption } from 'echarts';
import type { OHLCData, ChannelResult } from './indicators';

// ---------- 接口 ----------
export interface OverlayLine {
  name: string;
  lineType: string;   // 'upper' | 'middle' | 'lower' — 用于 tooltip 区分
  style: 'solid' | 'dashed';
  color: string;
  values: (number | '-')[];
}

export interface OverlayDef {
  id: string;
  legendName: string;
  color: string;
  lines: OverlayLine[];
}

// ---------- 工具函数 ----------
function buildLine(
  name: string,
  lineType: string,
  color: string,
  style: 'solid' | 'dashed',
  values: (number | '-')[],
): OverlayLine {
  return { name, lineType, color, style, values };
}

// ---------- 工厂函数 ----------
function donchianOverlay(
  period: number,
  color: string,
  ohlc: OHLCData[],
  dcData: (ChannelResult | null)[],
): OverlayDef {
  const upper = dcData.map((x) => x?.upper ?? '-');
  const middle = dcData.map((x) => x?.middle ?? '-');
  const lower = dcData.map((x) => x?.lower ?? '-');
  return {
    id: 'donchian',
    legendName: '唐奇安通道',
    color,
    lines: [
      buildLine('唐奇安通道', '上轨', color, 'dashed', upper),
      buildLine('唐奇安通道', '中轨', color, 'dashed', middle),
      buildLine('唐奇安通道', '下轨', color, 'dashed', lower),
    ],
  };
}

function bollOverlay(
  period: number,
  k: number,
  color: string,
  bollData: (ChannelResult | null)[],
): OverlayDef {
  const upper = bollData.map((x) => x?.upper ?? '-');
  const middle = bollData.map((x) => x?.middle ?? '-');
  const lower = bollData.map((x) => x?.lower ?? '-');
  return {
    id: 'boll',
    legendName: '布林带',
    color,
    lines: [
      buildLine('布林带', '上轨', color, 'solid', upper),
      buildLine('布林带', '中轨', color, 'dashed', middle),
      buildLine('布林带', '下轨', color, 'solid', lower),
    ],
  };
}

// ---------- 注册表构建 ----------
export function buildOverlays(
  ohlc: OHLCData[],
  dcData: (ChannelResult | null)[],
  bollData: (ChannelResult | null)[],
): OverlayDef[] {
  return [
    donchianOverlay(20, '#f5a742', ohlc, dcData),
    bollOverlay(20, 2, '#9b59b6', bollData),
  ];
}

// ---------- 渲染：overlay → ECharts series ----------
// series name = legendName（整组切换），data 带 lineType 供 tooltip formatter 使用
export function overlayToSeries(overlays: OverlayDef[]): EChartsSeriesOption[] {
  return overlays.flatMap((o) =>
    o.lines.map((line) => ({
      name: o.legendName,
      data: line.values.map((v) =>
        v === '-' ? '-' : { value: v, _lineType: line.lineType },
      ),
      type: 'line' as const,
      xAxisIndex: 0,
      yAxisIndex: 0,
      lineStyle: {
        color: line.color,
        width: 1,
        type: line.style === 'dashed' ? ('dashed' as const) : ('solid' as const),
      },
      showSymbol: false,
      smooth: false,
    })),
  );
}

// ---------- 渲染：overlay → legend data ----------
export function overlayToLegend(
  overlays: OverlayDef[],
): { name: string; icon: string }[] {
  // legend name 用 baseName（去掉上/中/下轨后缀），与 series name 匹配实现整组切换
  const seen = new Set<string>();
  const result: { name: string; icon: string }[] = [];
  for (const o of overlays) {
    if (!seen.has(o.legendName)) {
      seen.add(o.legendName);
      result.push({ name: o.legendName, icon: 'roundRect' });
    }
  }
  return result;
}

// ---------- 查找 overlay helper ----------
export function findOverlayById(
  overlays: OverlayDef[],
  id: string,
): OverlayDef | undefined {
  return overlays.find((o) => o.id === id);
}
