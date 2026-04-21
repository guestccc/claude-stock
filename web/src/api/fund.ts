/** 基金相关 API */
import client from './client'

export interface FundHistoryItem {
  date: string
  nav: number | null
  est_pct: number | null
}

export interface FundItem {
  code: string
  name: string
  fund_type: string
  company: string
  manager: string
  remark: string
  added_at: string
  nav: number | null
  nav_date: string
  est_nav: number | null
  est_pct: number | null
  update_time: string
  history: FundHistoryItem[]
  nav_change_pct: number | null
}

export interface FundSearchItem {
  code: string
  name: string
  fund_type: string
  company: string
}

/** 获取自选基金列表 */
export async function getFundWatchlist(): Promise<FundItem[]> {
  const { data } = await client.get('/fund/watchlist')
  return data.data
}

/** 添加自选基金 */
export async function addFundWatchlist(code: string, remark?: string): Promise<any> {
  return client.post(`/fund/watchlist/${code}`, null, { params: { remark } })
}

/** 移除自选基金 */
export async function removeFundWatchlist(code: string): Promise<any> {
  return client.delete(`/fund/watchlist/${code}`)
}

/** 搜索基金 */
export async function searchFund(keyword: string): Promise<FundSearchItem[]> {
  const { data } = await client.get('/fund/search', { params: { q: keyword } })
  return data
}
