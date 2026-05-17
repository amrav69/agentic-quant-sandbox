/**
 * PnLChart.jsx
 * Animated Recharts area/line chart showing simulated cumulative PnL curve.
 *
 * Props:
 *  - data      (array?)  : Override default mock data
 *  - height    (number)  : Chart height in px (default: 280)
 *  - symbol    (string?) : Label shown in header
 */
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts'
import { TrendingUp, TrendingDown } from 'lucide-react'

/* ── Mock PnL curve generator ─────────────────────────────────────────────── */
function generateMockPnL(days = 90) {
  const data = []
  let cumulative = 0
  // Seeded LCG for stable output every render
  let s = 9301
  const rand = () => {
    s = (s * 49297 + 233453) % 233280
    return s / 233280
  }

  const now = new Date()
  for (let i = days; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    // Realistic daily return: ~0.15% drift, ~1.2% vol
    const dailyReturn = (rand() - 0.46) * 1.8 + 0.18
    cumulative = parseFloat((cumulative + dailyReturn).toFixed(2))
    data.push({
      date:  date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      pnl:   cumulative,
      daily: parseFloat(dailyReturn.toFixed(2)),
    })
  }
  return data
}

const MOCK_DATA = generateMockPnL(90)

/* ── Custom Tooltip ─────────────────────────────────────────────────────────── */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const val  = payload[0]?.value ?? 0
  const pos  = val >= 0

  return (
    <div
      className="glass rounded-xl px-4 py-3 text-xs font-mono"
      style={{
        border:     `1px solid ${pos ? '#10b98140' : '#ef444440'}`,
        minWidth:   '130px',
        backdropFilter: 'blur(20px)',
      }}
    >
      <p className="mb-1.5" style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="font-semibold text-sm" style={{ color: pos ? '#10b981' : '#ef4444' }}>
        {pos ? '+' : ''}{val.toFixed(2)}%
      </p>
    </div>
  )
}

/* ── PnLChart ─────────────────────────────────────────────────────────────── */
export default function PnLChart({ data = MOCK_DATA, height = 280, symbol = 'BTC-USD' }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 300)
    return () => clearTimeout(t)
  }, [])

  const lastVal   = data[data.length - 1]?.pnl ?? 0
  const firstVal  = data[0]?.pnl ?? 0
  const isUp      = lastVal >= firstVal
  const totalPct  = (lastVal - firstVal).toFixed(2)
  const gradId    = 'pnlGrad'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="glass rounded-2xl overflow-hidden"
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b"
        style={{ borderColor: 'var(--border-glass)' }}>
        <div>
          <p className="text-xs uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>
            Cumulative PnL (90d)
          </p>
          <p className="font-mono text-xs" style={{ color: 'var(--accent)' }}>
            {symbol}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isUp
            ? <TrendingUp  size={16} style={{ color: '#10b981' }} />
            : <TrendingDown size={16} style={{ color: '#ef4444' }} />
          }
          <span
            className="font-mono font-bold text-lg"
            style={{ color: isUp ? '#10b981' : '#ef4444' }}
          >
            {isUp ? '+' : ''}{totalPct}%
          </span>
        </div>
      </div>

      {/* ── Chart ── */}
      <div className="px-2 pb-4 pt-3">
        {visible && (
          <ResponsiveContainer width="100%" height={height}>
            <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -10 }}>
              <defs>
                <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={isUp ? '#10b981' : '#ef4444'} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={isUp ? '#10b981' : '#ef4444'} stopOpacity={0}    />
                </linearGradient>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                vertical={false}
              />

              <XAxis
                dataKey="date"
                tick={{ fill: '#475569', fontSize: 10, fontFamily: 'monospace' }}
                tickLine={false}
                axisLine={false}
                interval={Math.floor(data.length / 6)}
              />

              <YAxis
                tick={{ fill: '#475569', fontSize: 10, fontFamily: 'monospace' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(0)}%`}
              />

              <Tooltip content={<CustomTooltip />} />

              <ReferenceLine
                y={0}
                stroke="rgba(255,255,255,0.12)"
                strokeDasharray="4 4"
              />

              <Area
                type="monotone"
                dataKey="pnl"
                stroke={isUp ? '#10b981' : '#ef4444'}
                strokeWidth={2}
                fill={`url(#${gradId})`}
                dot={false}
                activeDot={{
                  r: 4,
                  fill: isUp ? '#10b981' : '#ef4444',
                  stroke: 'var(--bg-primary)',
                  strokeWidth: 2,
                }}
                isAnimationActive
                animationDuration={1400}
                animationEasing="ease-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </motion.div>
  )
}
