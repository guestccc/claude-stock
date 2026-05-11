import { Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, theme, App as AntdApp } from 'antd'
import AppLayout from './components/layout/AppLayout'
import MarketPage from './pages/MarketPage'
import StockListPage from './pages/StockListPage'
import ScreenerPage from './pages/ScreenerPage'
import BacktestPage from './pages/BacktestPage'
import PortfolioPage from './pages/PortfolioPage'
import FundPage from './pages/FundPage'
import FundDetailPage from './pages/FundDetailPage'
import BoardPage from './pages/BoardPage'
import SettingsPage from './pages/SettingsPage'

const antdTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorBgBase: '#000000',
    colorTextBase: '#e5e7eb',
    colorPrimary: '#7aa4f5',
    colorBorder: '#1a1a1a',
    colorBgContainer: '#2d2d2d',
    colorBgElevated: '#2d2d2d',
    borderRadius: 6,
    fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
  },
}

export default function App() {
  return (
    <ConfigProvider theme={antdTheme}>
      <AntdApp>
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
            <Route path="/fund/:code" element={<FundDetailPage />} />
            <Route path="/board" element={<BoardPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </AntdApp>
    </ConfigProvider>
  )
}
