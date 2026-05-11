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

/** 强制刷新板块行情 */
export async function refreshIndustryBoards(): Promise<{ total: number; updated_at: string }> {
  const { data } = await client.post('/board/industry/refresh')
  return data
}
