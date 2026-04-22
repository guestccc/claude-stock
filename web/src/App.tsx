import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import MarketPage from './pages/MarketPage'
import StockListPage from './pages/StockListPage'
import ScreenerPage from './pages/ScreenerPage'
import BacktestPage from './pages/BacktestPage'
import PortfolioPage from './pages/PortfolioPage'
import FundPage from './pages/FundPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/market" replace />} />
        <Route path="/market" element={<MarketPage />} />
        <Route path="/market/:code" element={<MarketPage />} />
        <Route path="/stocks" element={<StockListPage />} />
        <Route path="/screener" element={<ScreenerPage />} />
        <Route path="/backtest" element={<BacktestPage />} />
        <Route path="/backtest/:code" element={<BacktestPage />} />
        <Route path="/portfolio" element={<PortfolioPage />} />
        <Route path="/fund" element={<FundPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
