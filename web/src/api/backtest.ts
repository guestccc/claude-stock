/** 回测相关 API */
import client from './client'

// ---------- 类型定义 ----------

export interface ExitStrategyInfo {
  key: string
  name: string
  description: string
}

export interface BacktestRequest {
  code: string
  start_date: string
  end_date?: string
  initial_capital: number
  exit_strategy: string
  tp_multiplier: number
  trailing_atr_k: number
  half_exit_pct: number
}

export interface TradeResult {
  entry_date: string
  exit_date: string
  entry_price: number
  exit_price: number
  stop_loss: number
  take_profit: number
  shares: number
  pnl: number
  pnl_r: number
  holding_days: number
  reason: string
  atr: number
  upper_band: number
  breakout_close: number
  breakout_exceed_pct: number
  exit_formula: string
  turtle_units?: { entry_date: string; entry_price: number; shares: number }[]
  turtle_unit_size?: number
}

export interface EquityPoint {
  date: string
  total: number
  equity: number
  position_value: number
  peak: number
  dd: number
  dd_pct: number
}

export interface KlineBar {
  date: string
  open: number | null
  close: number | null
  high: number | null
  low: number | null
  volume: number | null
  turnover: number | null
}

export interface BacktestStats {
  initial_capital: number
  final_capital: number
  total_return: number
  total_return_pct: number
  num_trades: number
  win_trades: number
  loss_trades: number
  win_rate: number
  avg_win: number
  avg_loss: number
  avg_pnl: number
  rr_ratio: number
  max_drawdown: number
  max_drawdown_pct: number
  max_dd_date: string | null
  sharpe_ratio: number
  avg_holding_days: number
  daily_return_pct: number
  best_trade: TradeResult | null
  worst_trade: TradeResult | null
}

export interface BacktestResponse {
  code: string
  name: string
  request: BacktestRequest
  stats: BacktestStats
  trades: TradeResult[]
  equity_curve: EquityPoint[]
  klines: KlineBar[]
}

export interface BacktestHistoryItem {
  id: number
  code: string
  name: string
  start_date: string
  end_date: string
  exit_strategy: string
  total_return_pct: number
  num_trades: number
  win_rate: number
  max_drawdown_pct: number
  created_at: string
}

export interface BacktestHistoryListResponse {
  items: BacktestHistoryItem[]
  total: number
}

export interface BacktestDetailResponse {
  id: number
  code: string
  name: string
  start_date: string
  end_date: string
  initial_capital: number
  exit_strategy: string
  tp_multiplier: number
  trailing_atr_k: number
  half_exit_pct: number
  stats: BacktestStats
  trades: TradeResult[]
  equity_curve: EquityPoint[]
  klines: KlineBar[]
  created_at: string
}

// ---------- API 调用 ----------

/** 获取出场策略列表 */
export async function getStrategies(): Promise<{ strategies: ExitStrategyInfo[] }> {
  const { data } = await client.get('/backtest/strategies')
  return data
}

/** 获取近期回测过的股票 */
export async function getRecentStocks(limit = 10): Promise<{ stocks: { code: string; name: string }[] }> {
  const { data } = await client.get('/backtest/recent-stocks', { params: { limit } })
  return data
}

/** 运行回测 */
export async function runBacktest(params: BacktestRequest): Promise<BacktestResponse> {
  const { data } = await client.post('/backtest/run', params)
  return data
}

/** 保存回测结果 */
export async function saveBacktest(result: BacktestResponse): Promise<{ id: number; message: string }> {
  const { data } = await client.post('/backtest/save', result)
  return data
}

/** 获取历史回测列表 */
export async function getBacktestHistory(params?: {
  page?: number
  page_size?: number
}): Promise<BacktestHistoryListResponse> {
  const { data } = await client.get('/backtest/history', { params })
  return data
}

/** 获取历史回测详情 */
export async function getBacktestDetail(id: number): Promise<BacktestDetailResponse> {
  const { data } = await client.get(`/backtest/history/${id}`)
  return data
}

/** 删除历史回测 */
export async function deleteBacktest(id: number): Promise<void> {
  await client.delete(`/backtest/history/${id}`)
}
