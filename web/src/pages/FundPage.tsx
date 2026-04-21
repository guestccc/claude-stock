/** 自选基金页 */
import { useState, useEffect, useCallback } from 'react'
import {
  getFundWatchlist,
  addFundWatchlist,
  removeFundWatchlist,
  type FundItem,
} from '../api/fund'
import { colors, fonts, changeColor, changeSign } from '../theme/tokens'

function fmt(v: number | null, d = 4): string {
  if (v == null) return '-'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d })
}

const S = {
  page: { maxWidth: 900, margin: '0 auto' },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontFamily: fonts.mono,
    fontSize: 14,
    color: colors.textPrimary,
    fontWeight: 600,
  },
  subtitle: {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.textMuted,
  },
  addPanel: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    display: 'flex',
    gap: 8,
    alignItems: 'center',
  },
  input: {
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    padding: '8px 12px',
    color: colors.textPrimary,
    fontSize: 13,
    fontFamily: fonts.mono,
    outline: 'none',
    width: 160,
  },
  btn: (bg = colors.accent) => ({
    padding: '8px 16px',
    borderRadius: 6,
    border: 'none',
    cursor: 'pointer',
    fontSize: 13,
    fontFamily: fonts.mono,
    fontWeight: 600,
    background: bg,
    color: '#fff',
    transition: 'opacity 0.15s',
  }),
  btnDanger: {
    padding: '4px 10px',
    borderRadius: 4,
    border: `1px solid ${colors.fall}`,
    background: 'transparent',
    color: colors.fall,
    cursor: 'pointer',
    fontSize: 12,
    fontFamily: fonts.mono,
  },
  card: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
    display: 'flex',
    gap: 16,
    alignItems: 'flex-start',
  },
  cardLeft: { flex: 1, minWidth: 0 },
  cardRight: { display: 'flex', flexDirection: 'column' as const, alignItems: 'flex-end', gap: 4 },
  fundName: {
    fontFamily: fonts.mono,
    fontSize: 14,
    color: colors.textPrimary,
    fontWeight: 600,
    marginBottom: 4,
  },
  fundCode: {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.textMuted,
    marginBottom: 4,
  },
  fundMeta: {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.textMuted,
  },
  estPct: (color: string) => ({
    fontFamily: fonts.mono,
    fontSize: 18,
    fontWeight: 700,
    color,
  }),
  estNav: {
    fontFamily: fonts.mono,
    fontSize: 12,
    color: colors.textMuted,
  },
  updateTime: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.textMuted,
  },
  navInfo: {
    display: 'flex',
    gap: 12,
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 6,
    flexWrap: 'wrap' as const,
  },
  navTag: {
    background: colors.bg,
    borderRadius: 4,
    padding: '2px 6px',
  },
  typeTag: (type: string) => {
    const map: Record<string, string> = {
      '混合型': '#7aa4f5', '股票型': '#e06666', '债券型': '#5cb85c',
      '指数型': '#f0ad4e', '货币型': '#5bc0de', 'QDII': '#9b59b6',
    }
    const color = map[type] || colors.accent
    return {
      display: 'inline-block',
      fontFamily: fonts.mono,
      fontSize: 10,
      color,
      background: color + '22',
      borderRadius: 4,
      padding: '2px 6px',
      marginRight: 6,
    }
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: 13,
    fontFamily: fonts.mono,
    marginTop: 8,
  },
  th: {
    padding: '6px 8px',
    textAlign: 'left' as const,
    color: colors.textLabel,
    fontSize: 10,
    borderBottom: `1px solid ${colors.border}`,
    whiteSpace: 'nowrap' as const,
  },
  td: {
    padding: '6px 8px',
    borderBottom: `1px solid ${colors.border}`,
    color: colors.textSecondary,
  },
  tdRight: { textAlign: 'right' as const },
  empty: {
    textAlign: 'center' as const,
    padding: 48,
    color: colors.textMuted,
    fontFamily: fonts.mono,
    fontSize: 13,
  },
  loading: {
    textAlign: 'center' as const,
    padding: 24,
    color: colors.textMuted,
    fontFamily: fonts.mono,
  },
  msg: (type: 'success' | 'error') => ({
    padding: '8px 12px',
    borderRadius: 6,
    fontSize: 13,
    fontFamily: fonts.mono,
    marginBottom: 12,
    background: type === 'success' ? colors.riseBg : colors.fallBg,
    color: type === 'success' ? colors.rise : colors.fall,
    border: `1px solid ${type === 'success' ? colors.rise : colors.fall}`,
  }),
}

export default function FundPage() {
  const [funds, setFunds] = useState<FundItem[]>([])
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [inputVal, setInputVal] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const showMsg = (type: 'success' | 'error', text: string) => {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 4000)
  }

  const loadFunds = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getFundWatchlist()
      setFunds(data)
    } catch (e) {
      showMsg('error', '加载失败: ' + (e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadFunds() }, [loadFunds])

  // 交易时段每30秒刷新
  useEffect(() => {
    const now = new Date()
    const isTrading = now.getDay() >= 1 && now.getDay() <= 5 &&
      ((now.getHours() >= 9 && now.getHours() < 11) || (now.getHours() >= 13 && now.getHours() < 15))
    if (!isTrading) return
    const interval = setInterval(loadFunds, 30_000)
    return () => clearInterval(interval)
  }, [loadFunds])

  const handleAdd = async () => {
    const code = inputVal.trim()
    if (!code) return
    if (!/^\d{6}$/.test(code)) {
      showMsg('error', '请输入6位基金代码')
      return
    }
    if (funds.some(f => f.code === code)) {
      showMsg('error', `${code} 已在自选列表中`)
      return
    }
    setSubmitting(true)
    try {
      await addFundWatchlist(code)
      setInputVal('')
      showMsg('success', `已添加 ${code}`)
      await loadFunds()
    } catch (e) {
      showMsg('error', '添加失败: ' + (e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleRemove = async (code: string, name: string) => {
    if (!confirm(`确定移除 ${name} (${code})？`)) return
    try {
      await removeFundWatchlist(code)
      showMsg('success', `已移除 ${name}`)
      await loadFunds()
    } catch (e) {
      showMsg('error', '移除失败: ' + (e as Error).message)
    }
  }

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <div style={S.title}>自选基金</div>
          <div style={S.subtitle}>盘中实时估值 · 每30秒自动刷新</div>
        </div>
      </div>

      {/* 录入 */}
      <div style={S.addPanel}>
        {msg && <div style={S.msg(msg.type)}>{msg.text}</div>}
        <input
          style={S.input}
          placeholder="基金代码"
          value={inputVal}
          onChange={e => setInputVal(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
        />
        <button
          style={S.btn()}
          onClick={handleAdd}
          disabled={submitting}
        >
          {submitting ? '添加中...' : '添加'}
        </button>
      </div>

      {/* 列表 */}
      {loading ? (
        <div style={S.loading}>加载中...</div>
      ) : funds.length === 0 ? (
        <div style={S.empty}>
          暂无自选基金<br />
          <span style={{ fontSize: 12 }}>输入基金代码添加</span>
        </div>
      ) : (
        funds.map(fund => (
          <div key={fund.code} style={S.card}>
            <div style={S.cardLeft}>
              <div style={S.fundName}>{fund.name}</div>
              <div style={S.fundCode}>{fund.code}</div>
              <div style={S.fundMeta}>
                {fund.fund_type && <span style={S.typeTag(fund.fund_type)}>{fund.fund_type}</span>}
                {fund.company}
              </div>

              <div style={S.navInfo}>
                <span>净值日期: <span style={S.navTag}>{fund.nav_date || '-'}</span></span>
                {fund.nav != null && (
                  <span>单位净值: <span style={S.navTag}>{fund.nav.toFixed(4)}</span></span>
                )}
                {fund.nav_change_pct != null && (
                  <span>近10日涨跌: <span style={{ color: changeColor(fund.nav_change_pct) }}>
                    {changeSign(fund.nav_change_pct)}
                  </span></span>
                )}
              </div>

              {fund.history && fund.history.length > 0 && (
                <table style={S.table}>
                  <thead>
                    <tr>
                      <th style={S.th}>日期</th>
                      <th style={{ ...S.th, ...S.tdRight }}>单位净值</th>
                      <th style={{ ...S.th, ...S.tdRight }}>估算涨跌</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fund.history.slice(-5).map((h, i) => (
                      <tr key={i}>
                        <td style={S.td}>{h.date}</td>
                        <td style={{ ...S.td, ...S.tdRight }}>{h.nav?.toFixed(4) || '-'}</td>
                        <td style={{ ...S.td, ...S.tdRight, color: changeColor(h.est_pct) }}>
                          {changeSign(h.est_pct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div style={S.cardRight}>
              {fund.est_pct != null ? (
                <>
                  <div style={S.estPct(changeColor(fund.est_pct))}>
                    {changeSign(fund.est_pct)}
                  </div>
                  {fund.est_nav != null && (
                    <div style={S.estNav}>估算净值 {fund.est_nav.toFixed(4)}</div>
                  )}
                  {fund.update_time && (
                    <div style={S.updateTime}>更新 {fund.update_time}</div>
                  )}
                </>
              ) : (
                <div style={{ ...S.estNav, fontSize: 13, color: colors.textMuted }}>
                  {fund.nav != null ? `净值 ${fund.nav.toFixed(4)}` : '暂无估值'}
                </div>
              )}

              <button
                style={S.btnDanger}
                onClick={() => handleRemove(fund.code, fund.name)}
              >
                移除
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
