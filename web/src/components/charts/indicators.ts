/** 指标计算函数（纯函数，无副作用） */
import type { DailyBar } from '../../api/market';

// ---------- 类型 ----------
export interface OHLCData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  pctChange: number | null; // API 直接返回的涨跌幅
}

export interface MACDResult {
  dif: number;
  dea: number;
  bar: number;
}

export interface KDJResult {
  k: number;
  d: number;
  j: number;
}

export interface ChannelResult {
  upper: number;
  middle: number;
  lower: number;
}

// ---------- 辅助 ----------
function toOHLC(data: DailyBar[]): OHLCData[] {
  return data.map((d, i) => {
    const prevClose = i > 0 ? (data[i - 1].close ?? 0) : 0;
    const pctChange =
      d.pct_change != null
        ? d.pct_change
        : prevClose ? ((d.close ?? 0) - prevClose) / prevClose * 100 : null;
    return {
      date: d.date,
      open: d.open ?? 0,
      high: d.high ?? 0,
      low: d.low ?? 0,
      close: d.close ?? 0,
      volume: d.volume ?? 0,
      pctChange,
    };
  });
}

// ---------- EMA ----------
export function ema(values: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i === 0) {
      result.push(values[i]);
    } else {
      result.push(values[i] * k + result[i - 1] * (1 - k));
    }
  }
  return result;
}

// ---------- MACD(6,13,5) ----------
export function macd(closes: number[]): MACDResult[] {
  const e6 = ema(closes, 6);
  const e13 = ema(closes, 13);
  const dif = e6.map((v, i) => v - e13[i]);
  const dea = ema(dif, 5);
  return closes.map((_, i) => ({
    dif: dif[i],
    dea: dea[i],
    bar: (dif[i] - dea[i]) * 2,
  }));
}

// ---------- KDJ(9,3,3) ----------
export function kdj(
  highs: number[],
  lows: number[],
  closes: number[],
  period = 9,
): KDJResult[] {
  const result: KDJResult[] = [];
  let pk = 50,
    pd = 50;
  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) {
      result.push({ k: 0, d: 0, j: 0 });
      continue;
    }
    const hh = Math.max(...highs.slice(i - period + 1, i + 1));
    const ll = Math.min(...lows.slice(i - period + 1, i + 1));
    const rsv =
      hh === ll ? 50 : ((closes[i] - ll) / (hh - ll)) * 100;
    const k = (pk * 2) / 3 + rsv / 3;
    const d = (pd * 2) / 3 + k / 3;
    result.push({ k, d, j: 3 * k - 2 * d });
    pk = k;
    pd = d;
  }
  return result;
}

// ---------- 唐奇安通道(20) ----------
export function donchian(
  highs: number[],
  lows: number[],
  period = 20,
): ChannelResult[] {
  return highs.map((_, i) => {
    if (i < period - 1) return null;
    const hh = Math.max(...highs.slice(i - period + 1, i + 1));
    const ll = Math.min(...lows.slice(i - period + 1, i + 1));
    return { upper: hh, middle: (hh + ll) / 2, lower: ll };
  });
}

// ---------- 布林带(20,2) ----------
export function boll(
  closes: number[],
  period = 20,
  k = 2,
): ChannelResult[] {
  return closes.map((_, i) => {
    if (i < period - 1) return null;
    const w = closes.slice(i - period + 1, i + 1);
    const mean = w.reduce((a, b) => a + b, 0) / period;
    const std = Math.sqrt(
      w.reduce((a, b) => a + (b - mean) ** 2, 0) / period,
    );
    return { upper: mean + k * std, middle: mean, lower: mean - k * std };
  });
}

// ---------- 聚合计算（一次遍历全部算出） ----------
export interface Indicators {
  volumes: number[];
  upColors: string[];
  macd: MACDResult[];
  kdj: KDJResult[];
  donchian: (ChannelResult | null)[];
  boll: (ChannelResult | null)[];
}

export function computeIndicators(
  data: DailyBar[],
  needMACD = true,
  needKDJ = true,
): Indicators {
  const closes = data.map((d) => d.close ?? 0);
  const highs = data.map((d) => d.high ?? 0);
  const lows = data.map((d) => d.low ?? 0);
  const volumes = data.map((d) => d.volume ?? 0);
  const upColors = data.map((d) =>
    d.close != null && d.open != null && d.close >= d.open
      ? '#e06666'
      : '#5cb85c',
  );

  return {
    volumes,
    upColors,
    macd: needMACD ? macd(closes) : [],
    kdj: needKDJ ? kdj(highs, lows, closes) : [],
    donchian: donchian(highs, lows, 20),
    boll: boll(closes, 20, 2),
  };
}

export { toOHLC };
