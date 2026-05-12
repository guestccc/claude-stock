/** 板块行情页 — 行业板块(新浪) + 概念板块(同花顺) + 关注 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Button, Select, Space, Segmented, message } from 'antd'
import { ReloadOutlined, StarOutlined, StarFilled } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getIndustryBoards,
  refreshIndustryBoards,
  getConceptBoards,
  refreshConceptBoards,
  getBoardWatchlist,
  addBoardWatch,
  removeBoardWatch,
  type IndustryBoard,
  type ConceptBoard,
} from '../api/board'
import { useAppSettings } from '../store/appSettings'

const changeColor = (v: number) => v > 0 ? '#e06666' : v < 0 ? '#5cb85c' : '#999'

// ---------- 行业板块列定义 ----------
const industryColumns: ColumnsType<IndustryBoard> = [
  {
    title: '排名',
    width: 60,
    align: 'center',
    render: (_, __, idx) => idx + 1,
  },
  {
    title: '板块名称',
    dataIndex: 'name',
    width: 120,
    render: (name: string) => <span style={{ fontWeight: 600 }}>{name}</span>,
    sorter: (a, b) => a.name.localeCompare(b.name, 'zh'),
  },
  {
    title: '涨跌幅',
    dataIndex: 'change_pct',
    width: 100,
    align: 'right',
    sorter: (a, b) => a.change_pct - b.change_pct,
    defaultSortOrder: 'descend',
    render: (v: number) => (
      <span style={{ color: changeColor(v), fontWeight: 600 }}>
        {v > 0 ? '+' : ''}{v.toFixed(2)}%
      </span>
    ),
  },
  {
    title: '涨跌额',
    dataIndex: 'change',
    width: 90,
    align: 'right',
    sorter: (a, b) => a.change - b.change,
    render: (v: number) => (
      <span style={{ color: changeColor(v) }}>
        {v > 0 ? '+' : ''}{v.toFixed(2)}
      </span>
    ),
  },
  {
    title: '平均价',
    dataIndex: 'avg_price',
    width: 90,
    align: 'right',
    render: (v: number) => v.toFixed(2),
  },
  {
    title: '成交量',
    dataIndex: 'volume',
    width: 110,
    align: 'right',
    sorter: (a, b) => a.volume - b.volume,
    render: (v: number) => (v / 1e8).toFixed(2) + '亿',
  },
  {
    title: '成交额',
    dataIndex: 'amount',
    width: 120,
    align: 'right',
    sorter: (a, b) => a.amount - b.amount,
    render: (v: number) => (v / 1e8).toFixed(2) + '亿',
  },
  {
    title: '股票数',
    dataIndex: 'stock_count',
    width: 70,
    align: 'center',
  },
  {
    title: '领涨股',
    width: 180,
    render: (_, record) => (
      <span>
        {record.lead_stock_name}
        <span style={{ color: changeColor(record.lead_stock_change_pct), marginLeft: 6, fontSize: 11 }}>
          {record.lead_stock_change_pct > 0 ? '+' : ''}{record.lead_stock_change_pct.toFixed(2)}%
        </span>
      </span>
    ),
  },
]

type BoardTab = 'industry' | 'concept'
type WatchFilter = 'all' | 'watched'

export default function BoardPage() {
  const [tab, setTab] = useState<BoardTab>('concept')
  const [industryData, setIndustryData] = useState<IndustryBoard[]>([])
  const [conceptData, setConceptData] = useState<ConceptBoard[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [watchedCodes, setWatchedCodes] = useState<Set<string>>(new Set())
  const [watchFilter, setWatchFilter] = useState<WatchFilter>('watched')
  const { fundCacheMinutes, setFundCacheMinutes } = useAppSettings()
  const navigate = useNavigate()

  // 加载关注列表
  const loadWatchlist = useCallback(async () => {
    try {
      const codes = await getBoardWatchlist()
      setWatchedCodes(new Set(codes))
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { loadWatchlist() }, [loadWatchlist])

  const loadData = useCallback(async (t: BoardTab) => {
    setLoading(true)
    try {
      if (t === 'industry') {
        const boards = await getIndustryBoards(fundCacheMinutes)
        setIndustryData(boards)
      } else {
        const boards = await getConceptBoards(fundCacheMinutes)
        setConceptData(boards)
      }
    } catch {
      message.error('板块数据加载失败')
    } finally {
      setLoading(false)
    }
  }, [fundCacheMinutes])

  useEffect(() => { loadData(tab) }, [tab, loadData])

  // 交易时段自动刷新
  useEffect(() => {
    const now = new Date()
    const isTrading = now.getDay() >= 1 && now.getDay() <= 5 &&
      ((now.getHours() >= 9 && now.getHours() < 11) || (now.getHours() >= 13 && now.getHours() < 15))
    if (!isTrading) return
    const interval = setInterval(() => loadData(tab), 30_000)
    return () => clearInterval(interval)
  }, [tab, loadData])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      if (tab === 'industry') {
        const res = await refreshIndustryBoards()
        message.success(`刷新完成，共 ${res.total} 个行业板块`)
      } else {
        const res = await refreshConceptBoards()
        message.success(`刷新完成，共 ${res.total} 个概念板块`)
      }
      await loadData(tab)
    } catch {
      message.error('刷新失败')
    } finally {
      setRefreshing(false)
    }
  }

  const toggleWatch = async (e: React.MouseEvent, code: string, name: string) => {
    e.stopPropagation()
    try {
      if (watchedCodes.has(code)) {
        await removeBoardWatch(code)
        setWatchedCodes((prev) => { const next = new Set(prev); next.delete(code); return next })
      } else {
        await addBoardWatch(code, name)
        setWatchedCodes((prev) => new Set(prev).add(code))
      }
    } catch {
      message.error('操作失败')
    }
  }

  // 概念板块列（带星标）
  const conceptColumns: ColumnsType<ConceptBoard> = useMemo(() => [
    {
      title: '',
      width: 36,
      align: 'center',
      render: (_, record) => (
        <span onClick={(e) => toggleWatch(e, record.code, record.name)} style={{ cursor: 'pointer' }}>
          {watchedCodes.has(record.code)
            ? <StarFilled style={{ color: '#faad14' }} />
            : <StarOutlined style={{ color: '#555' }} />}
        </span>
      ),
    },
    {
      title: '排名',
      width: 50,
      align: 'center',
      render: (_, __, idx) => idx + 1,
    },
    {
      title: '板块名称',
      dataIndex: 'name',
      width: 140,
      render: (name: string) => <span style={{ fontWeight: 600 }}>{name}</span>,
      sorter: (a, b) => a.name.localeCompare(b.name, 'zh'),
    },
    {
      title: '涨跌幅',
      dataIndex: 'change_pct',
      width: 100,
      align: 'right',
      sorter: (a, b) => a.change_pct - b.change_pct,
      defaultSortOrder: 'descend',
      render: (v: number) => (
        <span style={{ color: changeColor(v), fontWeight: 600 }}>
          {v > 0 ? '+' : ''}{v.toFixed(2)}%
        </span>
      ),
    },
    {
      title: '净流入',
      dataIndex: 'net_inflow',
      width: 100,
      align: 'right',
      sorter: (a, b) => a.net_inflow - b.net_inflow,
      render: (v: number) => (
        <span style={{ color: changeColor(v) }}>
          {v > 0 ? '+' : ''}{v.toFixed(2)}亿
        </span>
      ),
    },
    {
      title: '强度',
      dataIndex: 'strength',
      width: 70,
      align: 'center',
      sorter: (a, b) => a.strength - b.strength,
      render: (v: number) => {
        let color = '#999'
        if (v >= 80) color = '#e06666'
        else if (v >= 50) color = '#f0a050'
        else if (v >= 20) color = '#5cb85c'
        return <span style={{ color }}>{v}</span>
      },
    },
    {
      title: '领涨股',
      width: 120,
      render: (_, record) => (
        <span>
          {record.lead_stock_name || record.lead_stock_code}
          {record.lead_stock_name && (
            <span style={{ color: '#888', marginLeft: 4, fontSize: 11 }}>{record.lead_stock_code}</span>
          )}
        </span>
      ),
    },
  ], [watchedCodes])

  // 筛选后的概念板块数据
  const filteredConceptData = useMemo(() => {
    if (watchFilter === 'all') return conceptData
    return conceptData.filter((b) => watchedCodes.has(b.code))
  }, [conceptData, watchFilter, watchedCodes])

  const currentData = tab === 'industry' ? industryData : filteredConceptData
  const currentColumns = tab === 'industry' ? industryColumns : conceptColumns
  const sourceLabel = tab === 'industry' ? '新浪财经' : '同花顺'
  const totalCount = tab === 'industry' ? industryData.length : conceptData.length
  const countLabel = tab === 'industry' ? '个行业板块' : '个概念板块'

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
            <h2 style={{ margin: 0, fontSize: 16 }}>板块行情</h2>
            <Segmented
              size="small"
              value={tab}
              onChange={(v) => setTab(v as BoardTab)}
              options={[
                { label: '行业板块', value: 'industry' },
                { label: '概念板块', value: 'concept' },
              ]}
            />
            {tab === 'concept' && (
              <Segmented
                size="small"
                value={watchFilter}
                onChange={(v) => setWatchFilter(v as WatchFilter)}
                options={[
                  { label: `全部 ${totalCount}`, value: 'all' },
                  { label: `关注 ${watchedCodes.size}`, value: 'watched' },
                ]}
              />
            )}
          </div>
          <span style={{ fontSize: 11, color: '#888' }}>
            数据来源：{sourceLabel} · {currentData.length}{countLabel}
          </span>
        </div>
        <Space>
          <span style={{ fontSize: 11, color: '#888' }}>缓存</span>
          <Select
            value={fundCacheMinutes}
            onChange={setFundCacheMinutes}
            size="small"
            style={{ width: 90 }}
            options={[
              { value: 0, label: '实时' },
              { value: 1, label: '1分钟' },
              { value: 2, label: '2分钟' },
              { value: 5, label: '5分钟' },
              { value: 10, label: '10分钟' },
              { value: 30, label: '30分钟' },
            ]}
          />
          <Button
            icon={<ReloadOutlined />}
            size="small"
            loading={refreshing}
            onClick={handleRefresh}
          >
            刷新
          </Button>
        </Space>
      </div>

      <Table
        dataSource={currentData}
        columns={currentColumns as any[]}
        loading={loading}
        rowKey="code"
        size="small"
        pagination={false}
        scroll={{ x: tab === 'industry' ? 940 : 620 }}
        rowClassName={(_, idx) => idx % 2 === 0 ? '' : 'ant-table-row-striped'}
        onRow={(record: any) => ({
          onClick: () => {
            if (tab === 'concept') {
              navigate(`/board/concept/${encodeURIComponent(record.name)}?code=${encodeURIComponent(record.code)}`)
            }
          },
          style: tab === 'concept' ? { cursor: 'pointer' } : {},
        })}
      />
    </div>
  )
}
