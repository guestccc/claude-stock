/** 大盘热力云图 — 内嵌 52etf 热力图页面 */
export default function HeatmapPage() {
  return (
    <div style={{ width: '100%', height: 'calc(100vh - 52px)', overflow: 'hidden' }}>
      <iframe
        src="https://52etf.site/"
        style={{ width: '100%', height: '100%', border: 'none' }}
        title="大盘热力云图"
      />
    </div>
  )
}
