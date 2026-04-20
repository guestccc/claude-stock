/** 标记点注册表 — 可扩展的 Mark 插件 */
import type { MarkPointOption } from 'echarts';
import type { OHLCData } from './indicators';
import { findOverlayById } from './overlays';

// ---------- 接口 ----------
export interface MarkStyle {
  symbol: string;
  symbolSize: number;
  color: string;
}

export interface MarkDef {
  id: string;
  label: string;
  style: MarkStyle;
  detect(
    ohlc: OHLCData[],
    overlays: { id: string; lines: { values: (number | '-')[] }[] }[],
  ): MarkPointOption[];
}

// ---------- 突破标记（唐奇安上轨 + 布林上轨同时突破） ----------
const breakoutMark: MarkDef = {
  id: 'breakout',
  label: '突破',
  style: {
    symbol: 'pin',
    symbolSize: 40,
    color: '#9b59b6',
  },
  detect(ohlc, overlays) {
    const dc = findOverlayById(overlays, 'donchian');
    const bl = findOverlayById(overlays, 'boll');
    if (!dc || !bl) return [];

    // 唐奇安上轨 = lines[0]（上轨）
    const dcUpperValues = dc.lines[0]?.values ?? [];
    // 布林上轨 = lines[0]（上轨）
    const blUpperValues = bl.lines[0]?.values ?? [];

    const marks: MarkPointOption[] = [];
    for (let i = 0; i < ohlc.length; i++) {
      const close = ohlc[i].close;
      const dcU = dcUpperValues[i];
      const blU = blUpperValues[i];

      if (
        typeof dcU === 'number' &&
        typeof blU === 'number' &&
        close >= dcU &&
        close >= blU
      ) {
        marks.push({
          coord: [i, close],
          value: '突破',
          symbol: 'pin',
          symbolSize: 40,
          label: { color: '#fff', fontSize: 9, fontWeight: 'bold' },
        });
      }
    }
    return marks;
  },
};

// ---------- 注册表 ----------
export const marks: MarkDef[] = [breakoutMark];

// ---------- 渲染：mark → ECharts markPoint ----------
export function marksToMarkPoint(
  markDefs: MarkDef[],
  ohlc: OHLCData[],
  overlays: { id: string; lines: { values: (number | '-')[] }[] }[],
): MarkPointOption[] {
  return markDefs.flatMap((m) => m.detect(ohlc, overlays));
}
