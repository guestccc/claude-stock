/** 自选股 API */
import client from './client'

export interface WatchlistItem {
  id: number
  code: string
  name: string
  added_at: string
  sort_order: number
  note?: string
}

export interface WatchlistResponse {
  items: WatchlistItem[]
}

/** 获取自选股列表 */
export async function getWatchlist(): Promise<WatchlistItem[]> {
  const { data } = await client.get<WatchlistResponse>('/watchlist')
  return data.items
}

/** 添加自选股 */
export async function addWatchlist(code: string): Promise<WatchlistItem> {
  const { data } = await client.post<WatchlistItem>('/watchlist', { code })
  return data
}

/** 删除自选股 */
export async function removeWatchlist(id: number): Promise<void> {
  await client.delete(`/watchlist/${id}`)
}

/** 更新自选股（备注、排序等） */
export async function updateWatchlist(id: number, body: { note?: string; sort_order?: number }): Promise<WatchlistItem> {
  const { data } = await client.put<WatchlistItem>(`/watchlist/${id}`, body)
  return data
}
