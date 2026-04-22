/** 系统管理 API */
import client from './client'

export interface TaskRecord {
  task_id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: number | null
  finished_at: number | null
  message: string
  error: string | null
}

export interface SchedulerStatus {
  running: boolean
  job_count: number
  jobs: { id: string; name: string; next_run: string }[]
  updated_at: string | null
}

export interface SystemStatus {
  db_size_mb: number
  db_path: string
  status: string
}

/** 获取系统状态 */
export async function getSystemStatus(): Promise<SystemStatus> {
  const { data } = await client.get('/system/status')
  return data
}

/** 获取调度器状态 */
export async function getSchedulerStatus(): Promise<SchedulerStatus> {
  const { data } = await client.get('/system/scheduler')
  return data
}

/** 获取所有任务状态 */
export async function getTasks(): Promise<{ tasks: TaskRecord[] }> {
  const { data } = await client.get('/system/tasks')
  return data
}

/** 触发任务 */
export async function triggerTask(
  task: string,
  params?: Record<string, any>
): Promise<TaskRecord & { error?: string; message?: string }> {
  const { data } = await client.post(`/system/tasks/${task}`, null, { params })
  return data
}
