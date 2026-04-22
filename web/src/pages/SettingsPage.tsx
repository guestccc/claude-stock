/** 设置页 — 数据任务管理 */
import { useState, useEffect, useCallback } from 'react'
import {
  getSystemStatus,
  getSchedulerStatus,
  getTasks,
  triggerTask,
  type TaskRecord,
  type SchedulerStatus,
  type SystemStatus,
} from '../api/system'
import { colors, fonts } from '../theme/tokens'

interface TaskDef {
  key: string
  label: string
  desc: string
  taskId: string
}

const taskGroups = [
  {
    title: '数据更新',
    items: [
      { key: 'daily-update', label: '增量日线', desc: '更新最新交易日K线数据', taskId: 'daily_update' },
      { key: 'minute-update', label: '分时数据', desc: '获取1分钟分时行情', taskId: 'minute_update' },
      { key: 'financial-update', label: '财务数据', desc: '更新股票财务报表', taskId: 'financial_update' },
      { key: 'boards-update', label: '板块数据', desc: '更新概念和行业板块', taskId: 'boards_update' },
      { key: 'fund-estimation', label: '基金估值', desc: '更新自选基金实时估值', taskId: 'fund_estimation' },
    ],
  },
  {
    title: '数据维护',
    items: [
      { key: 'minute-cleanup', label: '清理分时', desc: '删除过期分时数据', taskId: 'minute_cleanup' },
      { key: 'daily-clean', label: '清洗日线', desc: '补全涨跌幅/振幅等字段', taskId: 'daily_clean' },
    ],
  },
]

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
  card: {
    background: colors.bgSecondary,
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
  },
  cardTitle: {
    fontFamily: fonts.mono,
    fontSize: 12,
    color: colors.textPrimary,
    fontWeight: 600,
    marginBottom: 12,
  },
  taskRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 0',
    borderBottom: `1px solid ${colors.border}`,
    gap: 12,
  },
  taskInfo: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 2,
    flex: 1,
    minWidth: 0,
  },
  taskLabel: {
    fontFamily: fonts.mono,
    fontSize: 13,
    color: colors.textPrimary,
  },
  taskDesc: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.textMuted,
  },
  taskRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    flexShrink: 0,
  },
  statusBadge: (status: string) => {
    let color = colors.textMuted
    if (status === 'running') color = colors.accent
    else if (status === 'completed') color = colors.rise
    else if (status === 'failed') color = colors.fall
    return {
      fontFamily: fonts.mono,
      fontSize: 11,
      color,
      padding: '2px 8px',
      borderRadius: 4,
      border: `1px solid ${color}44`,
      background: color + '11',
      whiteSpace: 'nowrap' as const,
    }
  },
  btn: (disabled: boolean) => ({
    padding: '6px 14px',
    borderRadius: 6,
    border: 'none',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: 12,
    fontFamily: fonts.mono,
    fontWeight: 600,
    background: disabled ? colors.border : colors.accent,
    color: '#fff',
    opacity: disabled ? 0.5 : 1,
    transition: 'opacity 0.15s',
    whiteSpace: 'nowrap' as const,
  }),
  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 0',
    fontFamily: fonts.mono,
    fontSize: 12,
    color: colors.textSecondary,
    borderBottom: `1px solid ${colors.border}`,
  },
  infoLabel: {
    color: colors.textMuted,
  },
  jobRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '4px 0',
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.textSecondary,
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
  empty: {
    textAlign: 'center' as const,
    padding: 24,
    color: colors.textMuted,
    fontFamily: fonts.mono,
    fontSize: 12,
  },
  dot: (color: string) => ({
    display: 'inline-block',
    width: 6,
    height: 6,
    borderRadius: '50%',
    background: color,
    marginRight: 6,
  }),
}

export default function SettingsPage() {
  const [tasks, setTasks] = useState<Record<string, TaskRecord>>({})
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null)
  const [sysStatus, setSysStatus] = useState<SystemStatus | null>(null)
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [loading, setLoading] = useState(true)

  const showMsg = (type: 'success' | 'error', text: string) => {
    setMsg({ type, text })
    setTimeout(() => setMsg(null), 4000)
  }

  const loadTasks = useCallback(async () => {
    try {
      const { tasks: list } = await getTasks()
      const map: Record<string, TaskRecord> = {}
      for (const t of list) {
        map[t.task_id] = t
      }
      setTasks(map)
    } catch (e) {
      // 静默失败，轮询继续
    }
  }, [])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [sched, sys] = await Promise.all([
        getSchedulerStatus(),
        getSystemStatus(),
      ])
      setScheduler(sched)
      setSysStatus(sys)
      await loadTasks()
    } catch (e) {
      showMsg('error', '加载系统信息失败')
    } finally {
      setLoading(false)
    }
  }, [loadTasks])

  useEffect(() => { loadAll() }, [loadAll])

  // 轮询任务状态
  useEffect(() => {
    const interval = setInterval(loadTasks, 3000)
    return () => clearInterval(interval)
  }, [loadTasks])

  const handleTrigger = async (taskKey: string, name: string) => {
    try {
      const result = await triggerTask(taskKey)
      if ('error' in result && result.error === 'already_running') {
        showMsg('error', result.message || '任务正在运行')
        return
      }
      showMsg('success', `已触发: ${name}`)
      await loadTasks()
    } catch (e) {
      showMsg('error', '触发失败: ' + (e as Error).message)
    }
  }

  const renderStatusText = (taskId: string) => {
    const t = tasks[taskId]
    if (!t) return '空闲'
    if (t.status === 'running') return '运行中...'
    if (t.status === 'completed') return '已完成'
    if (t.status === 'failed') return '失败'
    return '空闲'
  }

  const formatTime = (ts: number | null) => {
    if (!ts) return '-'
    const d = new Date(ts * 1000)
    return d.toLocaleTimeString('zh-CN', { hour12: false })
  }

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <div style={S.title}>设置</div>
          <div style={S.subtitle}>数据管理与系统状态</div>
        </div>
      </div>

      {msg && <div style={S.msg(msg.type)}>{msg.text}</div>}

      {loading ? (
        <div style={S.empty}>加载中...</div>
      ) : (
        <>
          {/* 调度器状态 */}
          <div style={S.card}>
            <div style={S.cardTitle}>调度器</div>
            {scheduler ? (
              <>
                <div style={S.infoRow}>
                  <span style={S.infoLabel}>状态</span>
                  <span style={{ fontFamily: fonts.mono, fontSize: 12, color: colors.textPrimary }}>
                    <span style={S.dot(scheduler.running ? colors.rise : colors.fall)} />
                    {scheduler.running ? '运行中' : '已停止'}
                  </span>
                </div>
                {scheduler.jobs?.length > 0 ? (
                  scheduler.jobs.map((job, i) => (
                    <div key={i} style={S.jobRow}>
                      <span>{job.name}</span>
                      <span style={{ color: colors.textMuted }}>{job.next_run}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ ...S.empty, padding: 12 }}>无调度任务</div>
                )}
                {scheduler.updated_at && (
                  <div style={{ ...S.jobRow, color: colors.textMuted, marginTop: 4 }}>
                    更新于 {scheduler.updated_at}
                  </div>
                )}
              </>
            ) : (
              <div style={S.empty}>无法获取调度器状态</div>
            )}
          </div>

          {/* 任务分组 */}
          {taskGroups.map(group => (
            <div key={group.title} style={S.card}>
              <div style={S.cardTitle}>{group.title}</div>
              {group.items.map(item => {
                const isRunning = tasks[item.taskId]?.status === 'running'
                return (
                  <div key={item.key} style={S.taskRow}>
                    <div style={S.taskInfo}>
                      <span style={S.taskLabel}>{item.label}</span>
                      <span style={S.taskDesc}>{item.desc}</span>
                    </div>
                    <div style={S.taskRight}>
                      <span style={S.statusBadge(tasks[item.taskId]?.status || '')}>
                        {renderStatusText(item.taskId)}
                      </span>
                      <span style={{ fontFamily: fonts.mono, fontSize: 10, color: colors.textMuted }}>
                        {formatTime(tasks[item.taskId]?.finished_at || tasks[item.taskId]?.started_at)}
                      </span>
                      <button
                        style={S.btn(isRunning)}
                        onClick={() => handleTrigger(item.key, item.label)}
                        disabled={isRunning}
                      >
                        {isRunning ? '运行中' : '执行'}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          ))}

          {/* 系统信息 */}
          {sysStatus && (
            <div style={S.card}>
              <div style={S.cardTitle}>系统信息</div>
              <div style={S.infoRow}>
                <span style={S.infoLabel}>数据库大小</span>
                <span>{sysStatus.db_size_mb} MB</span>
              </div>
              <div style={S.infoRow}>
                <span style={S.infoLabel}>数据库路径</span>
                <span style={{ wordBreak: 'break-all' as const }}>{sysStatus.db_path}</span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
