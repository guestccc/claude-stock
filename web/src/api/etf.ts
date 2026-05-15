/** ETF 相关 API */
import client from './client'

export interface ETFListItem {
  code: string
  name: string
  etf_type: string | null
  nav: number | null
  market_price: number | null
  discount_rate: number | null
}

/** ETF 列表 */
export async function getETFList(params?: {
  search?: string
  etf_type?: string
  page?: number
  page_size?: number
}): Promise<{ data: ETFListItem[]; total: number; page: number; page_size: number }> {
  const { data } = await client.get('/etf', { params })
  return data
}

/** ETF 详情 */
export interface ETFDetail extends ETFListItem {
  acc_nav: number | null
  latest_date: string | null
  open: number | null
  close: number | null
  high: number | null
  low: number | null
  volume: number | null
  turnover: number | null
  pct_change: number | null
  amplitude: number | null
  turnover_rate: number | null
}

export async function getETFDetail(code: string): Promise<ETFDetail> {
  const { data } = await client.get(`/etf/${code}`)
  return data
}

/** 搜索 ETF */
export interface ETFSearchItem {
  code: string
  name: string
  etf_type: string | null
}

export async function searchETFs(keyword: string, limit = 20): Promise<ETFSearchItem[]> {
  const { data } = await client.get('/etf/search', { params: { keyword, limit } })
  return data.results
}
