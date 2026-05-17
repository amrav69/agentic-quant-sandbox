/**
 * LiveTicker.jsx — Infinite horizontal marquee of live prices.
 * Hardware-accelerated, overflow-clipped, no jitter.
 */
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'

function TickerItem({ symbol, price, changePercent, positive }) {
  const color = positive ? '#10b981' : '#ef4444'
  const Icon  = positive ? TrendingUp : TrendingDown
  const sign  = positive ? '+' : ''

  return (
    <div className="inline-flex items-center gap-3 px-5 shrink-0 select-none">
      <span className="w-px h-3.5 shrink-0 opacity-30" style={{ background: 'var(--border-glass)', display: 'inline-block' }} />
      <span className="font-mono text-[12px] font-semibold tracking-wide" style={{ color: 'var(--accent)' }}>
        {symbol}
      </span>
      <span className="font-mono text-[12px]" style={{ color: 'var(--text-secondary)' }}>
        {typeof price === 'number'
          ? price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : price}
      </span>
      <span className="inline-flex items-center gap-1 font-mono text-[11px] font-medium" style={{ color }}>
        <Icon size={10} />
        {sign}{changePercent}%
      </span>
    </div>
  )
}

const DEFAULT_TICKERS = [
  { symbol: 'BTC-USD',  price: 78413.50, changePercent: '1.62',  positive: true  },
  { symbol: 'ETH-USD',  price: 3521.88,  changePercent: '1.18',  positive: false },
  { symbol: 'AAPL',     price: 300.22,   changePercent: '0.82',  positive: true  },
  { symbol: 'NVDA',     price: 875.60,   changePercent: '1.77',  positive: true  },
  { symbol: 'SOL-USD',  price: 148.33,   changePercent: '2.33',  positive: false },
  { symbol: 'TSLA',     price: 248.80,   changePercent: '2.94',  positive: true  },
  { symbol: 'SPY',      price: 512.40,   changePercent: '0.35',  positive: false },
  { symbol: 'DOGE-USD', price: 0.1422,   changePercent: '2.23',  positive: true  },
]

export default function LiveTicker({ items = DEFAULT_TICKERS, speed = 38 }) {
  /* Duplicate items for seamless loop. Estimate ~200px per item. */
  const doubled  = [...items, ...items]
  const duration = (items.length * 200) / speed

  return (
    <div
      style={{
        overflow:        'hidden',
        borderTop:       '1px solid var(--border-glass)',
        borderBottom:    '1px solid var(--border-glass)',
        position:        'relative',
        height:          40,
        display:         'flex',
        alignItems:      'center',
        background:      'rgba(0,0,0,0.2)',
      }}
    >
      {/* Left mask */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0, width: 80, zIndex: 2, pointerEvents: 'none',
        background: 'linear-gradient(to right, var(--bg-primary) 0%, transparent 100%)',
      }} />
      {/* Right mask */}
      <div style={{
        position: 'absolute', right: 0, top: 0, bottom: 0, width: 80, zIndex: 2, pointerEvents: 'none',
        background: 'linear-gradient(to left, var(--bg-primary) 0%, transparent 100%)',
      }} />

      {/* Track */}
      <motion.div
        className="ticker-track flex items-center"
        animate={{ x: ['0%', '-50%'] }}
        transition={{ duration, repeat: Infinity, ease: 'linear', repeatType: 'loop' }}
        style={{ willChange: 'transform' }}
      >
        {doubled.map((item, i) => (
          <TickerItem key={`${item.symbol}-${i}`} {...item} />
        ))}
      </motion.div>
    </div>
  )
}
