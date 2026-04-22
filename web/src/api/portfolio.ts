/** 持仓相关 API */
import client from './client'

export interface HoldingItem {
  id: number
  code: string
  name: string
  shares: number
  avg_cost: number
  total_cost: number
  current_price: number | null
  market_value: number | null
  profit_amount: number | null
  profit_pct: number | null
  first_buy_date: string | null
  note: string | null
  created_at: string
  updated_at: string
}

export interface HoldingSummary {
  total_cost: number
  total_market_value: number
  total_profit_amount: number
  total_profit_pct: number
  holding_count: number
}

export interface HoldingsResponse {
  holdings: HoldingItem[]
  summary: HoldingSummary
}

export interface TransactionItem {
  id: number
  code: string
  name: string
  type: 'buy' | 'sell'
  shares: number
  price: number
  amount: number
  fee: number
  date: string
  note: string | null
  created_at: string
}

export interface TransactionsResponse {
  transactions: TransactionItem[]
}

export interface TradeResult {
  message: string
  holding: HoldingItem | null
  transaction: TransactionItem
}

/** 获取持仓列表 */
export async function getHoldings(): Promise<HoldingsResponse> {
  const { data } = await client.get('/portfolio/holdings')
  return data
}

export interface ClosedPositionItem {
  code: string
  name: string
  total_buy: number
  total_sell: number
  profit: number
  profit_pct: number
  last_sell_date: string
}

export interface ClosedPositionsResponse {
  items: ClosedPositionItem[]
}

/** 获取已清仓列表 */
export async function getClosedPositions(): Promise<ClosedPositionsResponse> {
  const { data } = await client.get('/portfolio/closed')
  return data
}

/** 买入股票 */
export async function buyStock(params: {
  code: string
  shares: number
  price: number
  fee?: number
  date?: string
  note?: string
}): Promise<TradeResult> {
  const { data } = await client.post('/portfolio/buy', params)
  return data
}

/** 卖出股票 */
export async function sellStock(params: {
  code: string
  shares: number
  price: number
  fee?: number
  date?: string
  note?: string
}): Promise<TradeResult> {
  const { data } = await client.post('/portfolio/sell', params)
  return data
}

/** 获取交易记录 */
export async function getTransactions(params?: {
  code?: string
  limit?: number
}): Promise<TransactionsResponse> {
  const { data } = await client.get('/portfolio/transactions', { params })
  return data
}

/** 清仓（删除持仓） */
export async function removeHolding(code: string): Promise<void> {
  await client.delete(`/portfolio/holdings/${code}`)
}
