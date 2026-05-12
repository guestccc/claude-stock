/** 板块行情 API */
import client from './client'

export interface IndustryBoard {
  code: string
  name: string
  stock_count: number
  avg_price: number
  change: number
  change_pct: number
  volume: number
  amount: number
  lead_stock_code: string
  lead_stock_price: number
  lead_stock_change: number
  lead_stock_change_pct: number
  lead_stock_name: string
}

/** 获取行业板块行情 */
export async function getIndustryBoards(cacheMinutes?: number): Promise<IndustryBoard[]> {
  const params: any = {}
  if (cacheMinutes != null) params.cache_minutes = cacheMinutes
  const { data } = await client.get('/board/industry', { params })
  return data.data
}

export interface ConceptBoard {
  code: string
  name: string
  change_pct: number
  net_inflow: number
  strength: number
  lead_stock_code: string
  lead_stock_name?: string
}

/** 强制刷新行业板块行情 */
export async function refreshIndustryBoards(): Promise<{ total: number; updated_at: string }> {
  const { data } = await client.post('/board/industry/refresh')
  return data
}

/** 获取概念板块行情 */
export async function getConceptBoards(cacheMinutes?: number): Promise<ConceptBoard[]> {
  const params: any = {}
  if (cacheMinutes != null) params.cache_minutes = cacheMinutes
  const { data } = await client.get('/board/concept', { params })
  return data.data
}

/** 强制刷新概念板块行情 */
export async function refreshConceptBoards(): Promise<{ total: number; updated_at: string }> {
  const { data } = await client.post('/board/concept/refresh')
  return data
}

/** 获取概念板块指数 K 线 */
export async function getConceptKline(
  name: string,
  period?: string,
  code?: string,
): Promise<{ name: string; data: any[] }> {
  const params: any = {}
  if (period) params.period = period
  if (code) params.code = code
  const { data } = await client.get(`/board/concept/${encodeURIComponent(name)}/kline`, { params })
  return data
}

/** 获取关注的板块代码列表 */
export async function getBoardWatchlist(): Promise<string[]> {
  const { data } = await client.get('/board/watchlist')
  return data.data
}

/** 关注板块 */
export async function addBoardWatch(code: string, name: string): Promise<void> {
  await client.post(`/board/watchlist/${encodeURIComponent(code)}`, null, { params: { name } })
}

/** 取消关注板块 */
export async function removeBoardWatch(code: string): Promise<void> {
  await client.delete(`/board/watchlist/${encodeURIComponent(code)}`)
}
