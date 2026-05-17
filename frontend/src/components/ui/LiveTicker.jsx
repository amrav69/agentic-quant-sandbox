/**
 * LiveTicker.jsx
 * Infinite horizontal marquee of live market ticker symbols.
 *
 * Props:
 *  - items (array): [{ symbol, price, change, changePercent, positive }]
 *  - speed (number): pixels per second (default: 40)
 */
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'

/* ── Single Ticker Item ── */
function TickerItem({ symbol, price, change, changePercent, positive }) {
  const color = positive ? '#10b981' : '#ef4444'
  const Icon  = positive ? TrendingUp : TrendingDown

  return (
    <div className="flex items-center gap-3 px-6 shrink-0">
      {/* Separator */}
      <span className="w-px h-4 shrink-0" style={{ background: 'var(--border-glass)' }} />

      {/* Symbol */}
      <span className="font-mono text-xs font-semibold tracking-wider"
        style={{ color: 'var(--accent)' }}>
        {symbol}
      </span>

      {/* Price */}
      <span className="font-mono text-xs" style={{ color: 'var(--text-primary)' }}>
        {typeof price === 'number' ? price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : price}
      </span>

      {/* Change */}
      <div className="flex items-center gap-1">
        <Icon size={11} style={{ color }} />
        <span className="font-mono text-[11px] font-medium" style={{ color }}>
          {positive ? '+' : ''}{changePercent}%
        </span>
      </div>
    </div>
  )
}

/* ── Default ticker data (placeholder until real API data is wired) ── */
const DEFAULT_TICKERS = [
  { symbol: 'BTC-USD',  price: 78413.50, change: 1250.30, changePercent: '+1.62',  positive: true  },
  { symbol: 'ETH-USD',  price: 3521.88,  change: -42.10,  changePercent: '-1.18',  positive: false },
  { symbol: 'AAPL',     price: 300.22,   change: 2.44,    changePercent: '+0.82',  positive: true  },
  { symbol: 'NVDA',     price: 875.60,   change: 15.20,   changePercent: '+1.77',  positive: true  },
  { symbol: 'SOL-USD',  price: 148.33,   change: -3.55,   changePercent: '-2.33',  positive: false },
  { symbol: 'TSLA',     price: 248.80,   change: 7.10,    changePercent: '+2.94',  positive: true  },
  { symbol: 'SPY',      price: 512.40,   change: -1.80,   changePercent: '-0.35',  positive: false },
  { symbol: 'DOGE-USD', price: 0.1422,   change: 0.0031,  changePercent: '+2.23',  positive: true  },
]

export default function LiveTicker({ items = DEFAULT_TICKERS, speed = 40 }) {
  // Duplicate items for seamless infinite loop
  const doubled = [...items, ...items]

  // Calculate animation duration from content width estimate (each item ~180px)
  const duration = (items.length * 180) / speed

  return (
    <div className="glass border-y overflow-hidden py-2.5 relative"
      style={{ borderColor: 'var(--border-glass)' }}>

      {/* Left fade mask */}
      <div className="absolute left-0 top-0 bottom-0 w-16 z-10 pointer-events-none"
        style={{ background: 'linear-gradient(to right, var(--bg-primary), transparent)' }} />

      {/* Right fade mask */}
      <div className="absolute right-0 top-0 bottom-0 w-16 z-10 pointer-events-none"
        style={{ background: 'linear-gradient(to left, var(--bg-primary), transparent)' }} />

      {/* Scrolling ticker track */}
      <motion.div
        className="flex items-center"
        animate={{ x: ['0%', '-50%'] }}
        transition={{
          duration,
          repeat:    Infinity,
          ease:      'linear',
          repeatType: 'loop',
        }}
      >
        {doubled.map((item, i) => (
          <TickerItem key={`${item.symbol}-${i}`} {...item} />
        ))}
      </motion.div>
    </div>
  )
}
