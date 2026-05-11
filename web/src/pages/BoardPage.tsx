/** 板块行情页 — 行业板块实时涨跌 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { Table, Button, Select, Space, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getIndustryBoards,
  refreshIndustryBoards,
  type IndustryBoard,
} from '../api/board'
import { useAppSettings } from '../store/appSettings'

const changeColor = (v: number) => v > 0 ? '#e06666' : v < 0 ? '#5cb85c' : '#999'

const columns: ColumnsType<IndustryBoard> = [
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
    render: (name: string, record) => (
      <span style={{ fontWeight: 600 }}>{name}</span>
    ),
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

export default function BoardPage() {
  const [data, setData] = useState<IndustryBoard[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const { fundCacheMinutes, setFundCacheMinutes } = useAppSettings()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const loadData = useCallback(async () => {
    try {
      const boards = await getIndustryBoards(fundCacheMinutes)
      setData(boards)
    } catch {
      message.error('板块数据加载失败')
    } finally {
      setLoading(false)
    }
  }, [fundCacheMinutes])

  useEffect(() => { loadData() }, [loadData])

  // 交易时段自动刷新
  useEffect(() => {
    const now = new Date()
    const isTrading = now.getDay() >= 1 && now.getDay() <= 5 &&
      ((now.getHours() >= 9 && now.getHours() < 11) || (now.getHours() >= 13 && now.getHours() < 15))
    if (!isTrading) return
    const interval = setInterval(loadData, 30_000)
    return () => clearInterval(interval)
  }, [loadData])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const res = await refreshIndustryBoards()
      message.success(`刷新完成，共 ${res.total} 个板块`)
      await loadData()
    } catch {
      message.error('刷新失败')
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 16 }}>行业板块行情</h2>
          <span style={{ fontSize: 11, color: '#888' }}>
            数据来源：新浪财经 · {data.length} 个行业板块
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

      <Table<IndustryBoard>
        dataSource={data}
        columns={columns}
        loading={loading}
        rowKey="code"
        size="small"
        pagination={false}
        scroll={{ x: 940 }}
        rowClassName={(_, idx) => idx % 2 === 0 ? '' : 'ant-table-row- striped'}
      />
    </div>
  )
}
