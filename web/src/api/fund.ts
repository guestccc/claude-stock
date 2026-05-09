/** 基金相关 API */
import client from './client'

export interface FundHistoryItem {
  date: string
  nav: number | null
  pct_change: number | null
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

/** 基金详情 */
export interface FundDetail {
  code: string
  name: string
  full_name: string
  fund_type: string
  company: string
  manager: string
  setup_date: string
  scale: string
  benchmark: string
  strategy: string
  nav: number | null
  nav_date: string
  est_nav: number | null
  est_pct: number | null
  update_time: string
}

/** 基金历史净值数据点 */
export interface FundNavPoint {
  date: string
  nav: number
  pct_change: number | null
}

/** 获取基金详情 */
export async function getFundDetail(code: string): Promise<FundDetail> {
  const { data } = await client.get(`/fund/detail/${code}`)
  return data
}

/** 获取基金历史净值 */
export async function getFundNavHistory(
  code: string, period: string = '1年'
): Promise<{ code: string; period: string; data: FundNavPoint[] }> {
  const { data } = await client.get(`/fund/nav-history/${code}`, { params: { period } })
  return data
}

// ---------- 基金回测 ----------

export interface FundStrategyInfo {
  id: string
  name: string
  description: string
  params_desc: string
}

export interface StrategyParams {
  interval_days?: number
  amount?: number
  drop_pct?: number
  levels?: { drop_pct: number; amount: number }[]
  target_value?: number
  rebalance_days?: number
  grid_pct?: number
  amount_per_grid?: number
  take_profit_pct?: number
}

export interface FundBacktestRequest {
  code: string
  start_date: string
  end_date?: string
  initial_capital: number
  strategy: string
  params: StrategyParams
}

export interface FundTradeRecord {
  date: string
  type: string
  nav: number
  shares: number
  amount: number
  fee: number
  cash_after: number
  position_value_after: number
  reason: string
}

export interface FundEquityPoint {
  date: string
  nav: number
  total: number
  cash: number
  position_value: number
  shares: number
  cost_basis: number
}

export interface FundBacktestStats {
  initial_capital: number
  total_invested: number
  final_value: number
  total_return: number
  total_return_pct: number
  annualized_return_pct: number
  max_drawdown_pct: number
  max_drawdown_date: string
  sharpe_ratio: number | null
  num_trades: number
  num_buys: number
  num_sells: number
  avg_buy_amount: number
  final_shares: number
  final_nav: number
}

export interface FundBacktestResponse {
  code: string
  name: string
  strategy: string
  params: StrategyParams
  stats: FundBacktestStats
  trades: FundTradeRecord[]
  equity_curve: FundEquityPoint[]
}

/** 获取回测策略列表 */
export async function getFundBacktestStrategies(): Promise<FundStrategyInfo[]> {
  const { data } = await client.get('/fund/backtest/strategies')
  return data
}

/** 运行基金回测 */
export async function runFundBacktest(req: FundBacktestRequest): Promise<FundBacktestResponse> {
  const { data } = await client.post('/fund/backtest/run', req)
  return data
}
