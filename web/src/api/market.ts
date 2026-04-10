/** 行情相关 API */
import client from './client'

export interface StockInfo {
  code: string
  name: string
  type?: string
}

export interface DailyBar {
  date: string
  open: number | null
  close: number | null
  high: number | null
  low: number | null
  volume: number | null
  turnover: number | null
  pct_change: number | null
}

export interface QuoteItem {
  code: string
  name: string
  close: number | null
  change_pct: number | null
  volume: number | null
  turnover: number | null
}

/** 搜索股票 */
export async function searchStocks(keyword: string): Promise<StockInfo[]> {
  const { data } = await client.get('/market/search', { params: { q: keyword } })
  return data.results
}

/** 获取日 K 线 */
export async function getDaily(
  code: string,
  params?: { start?: string; end?: string; limit?: number }
): Promise<{ code: string; name: string; data: DailyBar[] }> {
  const { data } = await client.get(`/market/daily/${code}`, { params })
  return data
}

/** 批量行情 */
export async function getQuotes(codes: string[]): Promise<QuoteItem[]> {
  const { data } = await client.get('/market/quotes', { params: { codes: codes.join(',') } })
  return data.data
}
