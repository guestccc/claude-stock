/** 自选基金页 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Segmented,
  Table,
  Tag,
  Popconfirm,
  Input,
  Tooltip,
} from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getFundWatchlist,
  addFundWatchlist,
  removeFundWatchlist,
  updateFundTags,
  refreshFundEstimations,
  searchFund,
  type FundItem,
  type FundSearchItem,
} from '../api/fund'
import { colors, fonts, changeColor, changeSign } from '../theme/tokens'
import { useAppSettings } from '../store/appSettings'

function fmt(v: number | null, d = 4): string {
  if (v == null) return '-'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d })
}

const S = {
  page: { width: '100%' },
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
    position: 'relative' as const,
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
    width: 240,
  },
  dropdown: {
    position: 'absolute' as const,
    top: '100%',
    left: 16,
    width: 320,
    maxHeight: 260,
    overflowY: 'auto' as const,
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: 6,
    zIndex: 100,
    marginTop: 4,
    boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
  },
  dropdownItem: {
    padding: '8px 12px',
    cursor: 'pointer',
    borderBottom: `1px solid ${colors.border}`,
    display: 'flex',
    justifyContent: 'space-between' as const,
    alignItems: 'center',
  },
  dropdownItemName: {
    fontFamily: fonts.mono,
    fontSize: 12,
    color: colors.textPrimary,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
    maxWidth: 180,
  },
  dropdownItemCode: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.textMuted,
    flexShrink: 0,
  },
  dropdownItemType: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.accent,
    marginLeft: 6,
  },
  dropdownEmpty: {
    padding: '16px 12px',
    textAlign: 'center' as const,
    fontFamily: fonts.mono,
    fontSize: 12,
    color: colors.textMuted,
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
  userTag: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 3,
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.accent,
    background: colors.accent + '18',
    borderRadius: 4,
    padding: '2px 6px',
  },
  userTagRemove: {
    cursor: 'pointer',
    fontSize: 9,
    color: colors.textMuted,
    lineHeight: 1,
  },
  userTagAdd: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 18,
    height: 18,
    border: `1px dashed ${colors.border}`,
    borderRadius: 4,
    background: 'transparent',
    color: colors.textMuted,
    fontSize: 12,
    cursor: 'pointer',
    fontFamily: fonts.mono,
    padding: 0,
    lineHeight: 1,
  },
  tagInput: {
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    borderRadius: 4,
    padding: '2px 6px',
    color: colors.textPrimary,
    fontSize: 10,
    fontFamily: fonts.mono,
    outline: 'none',
    width: 140,
  },
  filterTagBtn: (active: boolean) => ({
    padding: '4px 10px',
    borderRadius: 4,
    border: 'none',
    cursor: 'pointer',
    fontSize: 11,
    fontFamily: fonts.mono,
    fontWeight: 600,
    background: active ? colors.accent : colors.bgSecondary,
    color: active ? '#fff' : colors.textSecondary,
    transition: 'all 0.15s',
  }),
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
  const navigate = useNavigate()
  const [funds, setFunds] = useState<FundItem[]>([])
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [inputVal, setInputVal] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [searchResults, setSearchResults] = useState<FundSearchItem[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [filterTag, setFilterTag] = useState<string>('')
  const [editingTags, setEditingTags] = useState<string | null>(null)
  const [tagInput, setTagInput] = useState('')
  const { fundCacheMinutes, setFundCacheMinutes } = useAppSettings()
  const [refreshing, setRefreshing] = useState(false)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')

  const showMsg = (type: 'success' | 'error', text: string) => {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 4000)
  }

  const loadFunds = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getFundWatchlist(fundCacheMinutes)
      setFunds(data)
    } catch (e) {
      showMsg('error', '加载失败: ' + (e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [fundCacheMinutes])

  // 首次加载 + 交易时段每30秒刷新
  const loadedRef = useRef(false)
  useEffect(() => {
    if (!loadedRef.current) {
      loadFunds()
      loadedRef.current = true
    }
    const now = new Date()
    const isTrading = now.getDay() >= 1 && now.getDay() <= 5 &&
      ((now.getHours() >= 9 && now.getHours() < 11) || (now.getHours() >= 13 && now.getHours() < 15))
    if (!isTrading) return
    const interval = setInterval(loadFunds, 30_000)
    return () => clearInterval(interval)
  }, [loadFunds])

  const handleAdd = async (code: string, name: string) => {
    if (funds.some(f => f.code === code)) {
      showMsg('error', `${name}(${code}) 已在自选列表中`)
      return
    }
    setSubmitting(true)
    try {
      await addFundWatchlist(code)
      setInputVal('')
      setSearchResults([])
      setShowDropdown(false)
      showMsg('success', `已添加 ${name}(${code})`)
      await loadFunds()
    } catch (e) {
      showMsg('error', '添加失败: ' + (e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleSaveTags = async (code: string) => {
    const newTags = tagInput.split(/[,，]/).map(t => t.trim()).filter(Boolean)
    try {
      await updateFundTags(code, newTags)
      setEditingTags(null)
      setTagInput('')
      await loadFunds()
    } catch (e) {
      showMsg('error', '标签保存失败: ' + (e as Error).message)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const res = await refreshFundEstimations()
      showMsg('success', `估值刷新完成：成功${res.success}只，失败${res.failed}只`)
      await loadFunds()
    } catch (e) {
      showMsg('error', '刷新失败: ' + (e as Error).message)
    } finally {
      setRefreshing(false)
    }
  }

  // 搜索防抖
  const handleInputChange = (val: string) => {
    setInputVal(val)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    if (!val.trim()) {
      setSearchResults([])
      setShowDropdown(false)
      return
    }
    setShowDropdown(true)
    setSearchLoading(true)
    searchTimerRef.current = setTimeout(async () => {
      try {
        const results = await searchFund(val.trim())
        setSearchResults(results)
      } catch {
        setSearchResults([])
      } finally {
        setSearchLoading(false)
      }
    }, 300)
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Segmented
            size="small"
            options={[{ label: '卡片', value: 'card' }, { label: '表格', value: 'table' }]}
            value={viewMode}
            onChange={v => setViewMode(v as 'card' | 'table')}
          />
          <label style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.textMuted, display: 'flex', alignItems: 'center', gap: 4 }}>
            缓存
            <select style={S.input}
              value={fundCacheMinutes}
              onChange={e => setFundCacheMinutes(+e.target.value)}
            >
              <option value={0}>实时</option>
              <option value={1}>1分钟</option>
              <option value={2}>2分钟</option>
              <option value={5}>5分钟</option>
              <option value={10}>10分钟</option>
              <option value={30}>30分钟</option>
            </select>
          </label>
          <button style={S.btn()} onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? '刷新中...' : '获取最新估值'}
          </button>
        </div>
      </div>

      {/* 录入 */}
      <div style={S.addPanel}>
        {msg && <div style={S.msg(msg.type)}>{msg.text}</div>}
        <input
          style={S.input}
          placeholder="输入基金代码或名称搜索"
          value={inputVal}
          onChange={e => handleInputChange(e.target.value)}
          onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
        />
        {showDropdown && (
          <div style={S.dropdown}>
            {searchLoading ? (
              <div style={S.dropdownEmpty}>搜索中...</div>
            ) : searchResults.length === 0 ? (
              <div style={S.dropdownEmpty}>无搜索结果</div>
            ) : (
              searchResults.map(item => (
                <div
                  key={item.code}
                  style={S.dropdownItem}
                  onClick={() => handleAdd(item.code, item.name)}
                >
                  <div>
                    <span style={S.dropdownItemName}>{item.name}</span>
                    {item.fund_type && <span style={S.dropdownItemType}>{item.fund_type}</span>}
                  </div>
                  <span style={S.dropdownItemCode}>{item.code}</span>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* 标签筛选栏 */}
      {(() => {
        const allTags = Array.from(new Set(funds.flatMap(f => f.tags))).sort()
        if (allTags.length === 0) return null
        return (
          <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
            <button
              style={S.filterTagBtn(!filterTag)}
              onClick={() => setFilterTag('')}
            >全部</button>
            {allTags.map(tag => (
              <button key={tag}
                style={S.filterTagBtn(filterTag === tag)}
                onClick={() => setFilterTag(filterTag === tag ? '' : tag)}
              >{tag}</button>
            ))}
          </div>
        )
      })()}

      {/* 列表 */}
      {loading ? (
        <div style={S.loading}>加载中...</div>
      ) : funds.length === 0 ? (
        <div style={S.empty}>
          暂无自选基金<br />
          <span style={{ fontSize: 12 }}>输入基金代码添加</span>
        </div>
      ) : viewMode === 'table' ? (
        /* ---- 表格视图 ---- */
        (() => {
          const filtered = funds.filter(f => !filterTag || f.tags.includes(filterTag))
          const tableColumns: ColumnsType<FundItem> = [
            {
              title: '基金名称',
              dataIndex: 'name',
              key: 'name',
              width: 220,
              sorter: (a, b) => a.name.localeCompare(b.name, 'zh'),
              render: (name: string, r: FundItem) => (
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{name}</div>
                  <div style={{ fontSize: 11, color: colors.textMuted }}>{r.code}</div>
                  {r.fund_type && (
                    <Tag
                      style={{ fontSize: 10, marginTop: 2, marginRight: 0, padding: '0 4px', borderRadius: 3 }}
                      color={
                        ({ '混合型': 'blue', '股票型': 'red', '债券型': 'green',
                           '指数型': 'orange', '货币型': 'cyan', 'QDII': 'purple' } as Record<string, string>)[r.fund_type]
                      }
                    >{r.fund_type}</Tag>
                  )}
                </div>
              ),
            },
            {
              title: '基金公司',
              dataIndex: 'company',
              key: 'company',
              width: 140,
              ellipsis: true,
              sorter: (a, b) => a.company.localeCompare(b.company, 'zh'),
              render: (v: string) => <span style={{ fontSize: 12 }}>{v}</span>,
            },
            {
              title: '单位净值',
              dataIndex: 'nav',
              key: 'nav',
              width: 100,
              align: 'right',
              sorter: (a, b) => (a.nav ?? 0) - (b.nav ?? 0),
              render: (v: number | null) => <span style={{ fontSize: 12 }}>{fmt(v)}</span>,
            },
            {
              title: '估值涨跌',
              dataIndex: 'est_pct',
              key: 'est_pct',
              width: 100,
              align: 'right',
              sorter: (a, b) => (a.est_pct ?? 0) - (b.est_pct ?? 0),
              render: (v: number | null) => (
                <span style={{ color: changeColor(v), fontWeight: 700, fontSize: 13 }}>
                  {changeSign(v)}
                </span>
              ),
            },
            {
              title: '估算净值',
              dataIndex: 'est_nav',
              key: 'est_nav',
              width: 100,
              align: 'right',
              sorter: (a, b) => (a.est_nav ?? 0) - (b.est_nav ?? 0),
              render: (v: number | null) => <span style={{ fontSize: 12 }}>{fmt(v)}</span>,
            },
            {
              title: '近10日涨跌',
              dataIndex: 'nav_change_pct',
              key: 'nav_change_pct',
              width: 110,
              align: 'right',
              sorter: (a, b) => (a.nav_change_pct ?? 0) - (b.nav_change_pct ?? 0),
              render: (v: number | null) => (
                <span style={{ color: changeColor(v), fontSize: 12 }}>{changeSign(v)}</span>
              ),
            },
            {
              title: '标签',
              dataIndex: 'tags',
              key: 'tags',
              width: 200,
              render: (tags: string[], r: FundItem) => (
                <div onClick={e => e.stopPropagation()} style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
                  {tags.map(tag => (
                    <Tag
                      key={tag}
                      closable
                      onClose={() => {
                        const newTags = tags.filter(t => t !== tag)
                        updateFundTags(r.code, newTags).then(loadFunds)
                      }}
                      style={{ fontSize: 10, padding: '0 4px', borderRadius: 3 }}
                    >{tag}</Tag>
                  ))}
                  {editingTags === r.code ? (
                    <Input
                      size="small"
                      autoFocus
                      value={tagInput}
                      onChange={e => setTagInput(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') handleSaveTags(r.code)
                        if (e.key === 'Escape') { setEditingTags(null); setTagInput('') }
                      }}
                      onBlur={() => handleSaveTags(r.code)}
                      placeholder="逗号分隔"
                      style={{ width: 100, fontSize: 10 }}
                    />
                  ) : (
                    <Tooltip title="编辑标签">
                      <Tag
                        style={{ cursor: 'pointer', borderStyle: 'dashed', fontSize: 10, padding: '0 4px', borderRadius: 3 }}
                        onClick={() => { setEditingTags(r.code); setTagInput(r.tags.join(',')) }}
                      >
                        <PlusOutlined /> 标签
                      </Tag>
                    </Tooltip>
                  )}
                </div>
              ),
            },
            {
              title: '操作',
              key: 'action',
              width: 60,
              align: 'center',
              render: (_: unknown, r: FundItem) => (
                <Popconfirm
                  title={`确定移除 ${r.name}？`}
                  onConfirm={() => handleRemove(r.code, r.name)}
                  okText="确定"
                  cancelText="取消"
                >
                  <DeleteOutlined style={{ color: colors.fall, cursor: 'pointer' }} onClick={e => e.stopPropagation()} />
                </Popconfirm>
              ),
            },
          ]
          return (
            <Table<FundItem>
              columns={tableColumns}
              dataSource={filtered}
              rowKey="code"
              size="small"
              pagination={false}
              onRow={record => ({
                onClick: () => navigate(`/fund/${record.code}`),
                style: { cursor: 'pointer' },
              })}
            />
          )
        })()
      ) : (
        /* ---- 卡片视图（原有逻辑） ---- */
        funds.filter(f => !filterTag || f.tags.includes(filterTag)).map(fund => (
          <div key={fund.code} style={{ ...S.card, cursor: 'pointer' }}
            onClick={() => navigate(`/fund/${fund.code}`)}
          >
            <div style={S.cardLeft}>
              <div style={S.fundName}>{fund.name}</div>
              <div style={S.fundCode}>{fund.code}</div>
              <div style={S.fundMeta}>
                {fund.fund_type && <span style={S.typeTag(fund.fund_type)}>{fund.fund_type}</span>}
                {fund.company}
              </div>

              {/* 标签 */}
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4, alignItems: 'center' }}
                onClick={e => e.stopPropagation()}
              >
                {fund.tags.map(tag => (
                  <span key={tag} style={S.userTag}>
                    {tag}
                    <span style={S.userTagRemove}
                      onClick={() => {
                        const newTags = fund.tags.filter(t => t !== tag)
                        updateFundTags(fund.code, newTags).then(loadFunds)
                      }}
                    >x</span>
                  </span>
                ))}
                {editingTags === fund.code ? (
                  <input
                    style={S.tagInput}
                    autoFocus
                    value={tagInput}
                    onChange={e => setTagInput(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') handleSaveTags(fund.code)
                      if (e.key === 'Escape') { setEditingTags(null); setTagInput('') }
                    }}
                    onBlur={() => handleSaveTags(fund.code)}
                    placeholder="输入标签，逗号分隔"
                  />
                ) : (
                  <button style={S.userTagAdd}
                    onClick={() => { setEditingTags(fund.code); setTagInput(fund.tags.join(',')) }}
                  >+</button>
                )}
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
                      <th style={{ ...S.th, ...S.tdRight }}>日增长率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fund.history.slice(-5).map((h, i) => (
                      <tr key={i}>
                        <td style={S.td}>{h.date}</td>
                        <td style={{ ...S.td, ...S.tdRight }}>{h.nav?.toFixed(4) || '-'}</td>
                        <td style={{ ...S.td, ...S.tdRight, color: changeColor(h.pct_change) }}>
                          {h.pct_change != null ? (h.pct_change >= 0 ? '+' : '') + h.pct_change.toFixed(2) + '%' : '-'}
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
                onClick={e => { e.stopPropagation(); handleRemove(fund.code, fund.name) }}
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
