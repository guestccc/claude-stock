/** 副图注册表 — 可扩展的 SubChart 插件 */
import type { EChartsSeriesOption } from 'echarts';
import type {
  OHLCData,
  MACDResult,
  KDJResult,
  Indicators,
} from './indicators';

// ---------- 类型 ----------
export type SubType = 'VOL' | 'MACD' | 'KDJ';

export interface SubChartDef {
  id: SubType;
  label: string;
  color: string;
  buildSeries(ohlc: OHLCData[], ind: Indicators): EChartsSeriesOption[];
}

// ---------- VOL 副图 ----------
const volSubChart: SubChartDef = {
  id: 'VOL',
  label: '成交量',
  color: '#f5a742',
  buildSeries(ohlc, ind) {
    return [
      {
        name: '成交量',
        type: 'bar' as const,
        id: 'vol',
        data: ohlc.map((d, i) => ({
          value: d.volume,
          itemStyle: { color: ind.upColors[i] },
        })),
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
    ];
  },
};

// ---------- MACD 副图 ----------
const macdSubChart: SubChartDef = {
  id: 'MACD',
  label: 'MACD(6,13,5)',
  color: '#7aa4f5',
  buildSeries(_ohlc, ind) {
    const m = ind.macd;
    return [
      {
        name: 'DIF',
        type: 'line' as const,
        id: 'macd-dif',
        data: m.map((x) => x.dif),
        smooth: true,
        lineStyle: { color: '#7aa4f5', width: 1 },
        showSymbol: false,
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      {
        name: 'DEA',
        type: 'line' as const,
        id: 'macd-dea',
        data: m.map((x) => x.dea),
        smooth: true,
        lineStyle: { color: '#f5a742', width: 1 },
        showSymbol: false,
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      {
        name: 'MACD',
        type: 'bar' as const,
        id: 'macd-bar',
        data: m.map((x) => ({
          value: x.bar,
          itemStyle: { color: x.bar >= 0 ? '#e06666' : '#5cb85c' },
        })),
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
    ];
  },
};

// ---------- KDJ 副图 ----------
const kdjSubChart: SubChartDef = {
  id: 'KDJ',
  label: 'KDJ(9,3,3)',
  color: '#f5a742',
  buildSeries(_ohlc, ind) {
    const k = ind.kdj;
    return [
      {
        name: 'K',
        type: 'line' as const,
        id: 'kdj-k',
        data: k.map((x) => (x.k !== 0 ? x.k : '-')),
        smooth: true,
        lineStyle: { color: '#e06666', width: 1 },
        showSymbol: false,
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      {
        name: 'D',
        type: 'line' as const,
        id: 'kdj-d',
        data: k.map((x) => (x.d !== 0 ? x.d : '-')),
        smooth: true,
        lineStyle: { color: '#7aa4f5', width: 1 },
        showSymbol: false,
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
      {
        name: 'J',
        type: 'line' as const,
        id: 'kdj-j',
        data: k.map((x) => (x.j !== 0 ? x.j : '-')),
        smooth: true,
        lineStyle: { color: '#f5a742', width: 1 },
        showSymbol: false,
        xAxisIndex: 0,
        yAxisIndex: 0,
      },
    ];
  },
};

// ---------- 注册表 ----------
export const subCharts: SubChartDef[] = [volSubChart, macdSubChart, kdjSubChart];

export const allSubTypes: SubType[] = ['VOL', 'MACD', 'KDJ'];

// ---------- 渲染：将 subChart series 的 gridIndex/yAxisIndex 重映射 ----------
export function buildSubSeries(
  activeTypes: SubType[],
  ohlc: OHLCData[],
  ind: Indicators,
  offsetGridIdx: number,
): EChartsSeriesOption[] {
  return activeTypes.flatMap((type, idx) => {
    const def = subCharts.find((s) => s.id === type);
    if (!def) return [];
    const raw = def.buildSeries(ohlc, ind);
    const realGridIdx = offsetGridIdx + idx;
    // 重映射 xAxisIndex / yAxisIndex
    return raw.map((s) => ({
      ...s,
      xAxisIndex: realGridIdx,
      yAxisIndex: realGridIdx,
    }));
  });
}
