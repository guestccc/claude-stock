/** 行情页 */
import { useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { colors } from '../theme/tokens';
import { getDaily, type DailyBar } from '../api/market';
import KlineChart from '../components/charts/KlineChart';
import WatchlistPanel from '../components/stock/WatchlistPanel';

export default function MarketPage() {
  const { code: urlCode } = useParams();
  const [code, setCode] = useState(urlCode || '600584');
  const [name, setName] = useState('');
  const [dailyData, setDailyData] = useState<DailyBar[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (urlCode) setCode(urlCode);
  }, [urlCode]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getDaily(code, { limit: 120 })
      .then((res) => {
        if (!cancelled) {
          setDailyData(res.data);
          setName(res.name);
        }
      })
      .catch(() => {
        if (!cancelled) setDailyData([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [code]);

  // 最新数据
  const latest = dailyData.length > 0 ? dailyData[dailyData.length - 1] : null;
  const prev = dailyData.length > 1 ? dailyData[dailyData.length - 2] : null;

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      {/* 左侧：K 线 + 指标 */}
      <div
        style={{
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        {/* 指标卡片 */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(5, 1fr)',
            gap: 12,
          }}
        >
          <StatCard
            label='代码'
            value={`${code} ${name}`}
            accent
          />
          <StatCard label='最新价' value={latest?.close?.toFixed(2) ?? '-'} />
          <ChangeCard pctChange={latest?.pct_change} close={latest?.close} prevClose={prev?.close} />
          <StatCard
            label='今开 / 昨收'
            value={
              latest
                ? `${latest.open?.toFixed(2) ?? '-'} / ${prev?.close?.toFixed(2) ?? '-'}`
                : '-'
            }
          />
          <StatCard
            label='最高 / 最低'
            value={
              latest
                ? `${latest.high?.toFixed(2) ?? '-'} / ${latest.low?.toFixed(2) ?? '-'}`
                : '-'
            }
          />
        </div>

        {/* K线图 */}
        {loading ? (
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: colors.textMuted,
            }}
          >
            加载中...
          </div>
        ) : dailyData.length > 0 ? (
          <KlineChart data={dailyData} height={680} />
        ) : (
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: colors.textMuted,
            }}
          >
            搜索股票查看 K 线图
          </div>
        )}
      </div>

      {/* 右侧：自选股面板 */}
      <WatchlistPanel />
    </div>
  );
}

/** 涨幅卡片 — 红涨绿跌 */
function ChangeCard({
  pctChange,
  close,
  prevClose,
}: {
  pctChange: number | null | undefined;
  close: number | null | undefined;
  prevClose: number | null | undefined;
}) {
  const pct = pctChange ?? (close != null && prevClose ? ((close - prevClose) / prevClose) * 100 : null);
  const isUp = pct != null && pct >= 0;
  const color = pct == null ? colors.textMuted : isUp ? '#e06666' : '#5cb85c';
  const text = pct != null ? `${isUp ? '+' : ''}${pct.toFixed(2)}%` : '-';

  return (
    <div style={{ background: colors.bgCard, borderRadius: 8, padding: 14 }}>
      <div style={{ fontSize: 10, color: colors.textLabel, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>
        涨跌幅
      </div>
      <div style={{ fontSize: 18, color, fontWeight: 700, fontFamily: 'inherit' }}>
        {text}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      style={{
        background: accent ? colors.accentBg : colors.bgCard,
        borderRadius: 8,
        padding: 14,
        border: accent ? `1px solid ${colors.accent}` : '1px solid transparent',
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: accent ? colors.accent : colors.textLabel,
          textTransform: 'uppercase',
          letterSpacing: 0.5,
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 18,
          color: accent ? colors.accent : colors.textPrimary,
          fontWeight: accent ? 700 : 600,
          fontFamily: 'inherit',
        }}
      >
        {value}
      </div>
    </div>
  );
}
