/**
 * ResearchPanel.jsx
 * Step 1 agent card — shows live indicators + AI analysis with staggered reveal.
 */
import { motion } from 'framer-motion'
import { Cpu } from 'lucide-react'
import { staggerContainer, fadeUp } from '../animations/motionVariants'

function IndicatorPill({ label, value }) {
  return (
    <div className="glass rounded-lg px-3 py-2 text-center">
      <p className="text-[10px] uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="font-mono text-xs font-semibold" style={{ color: 'var(--accent)' }}>
        {typeof value === 'number' ? value.toFixed(2) : (value ?? '—')}
      </p>
    </div>
  )
}

export default function ResearchPanel({ analysisText = '', indicators = {} }) {
  // Split into paragraphs for staggered reveal
  const paragraphs = analysisText.split('\n').filter(Boolean)

  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="visible"
      className="rounded-2xl overflow-hidden"
      style={{ border: '2px solid rgba(0,245,255,0.35)', background: 'rgba(0,245,255,0.03)', boxShadow: '0 0 40px rgba(0,245,255,0.08)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'rgba(0,245,255,0.15)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'rgba(0,245,255,0.12)' }}>
            <Cpu size={16} style={{ color: '#00f5ff' }} />
          </div>
          <div>
            <p className="font-semibold text-sm">Research Agent</p>
            <p className="text-[10px] uppercase tracking-widest" style={{ color: '#00f5ff' }}>Step 1 · Analysis Complete</p>
          </div>
        </div>
        <span className="text-[11px] font-mono px-3 py-1 rounded-full" style={{ color: '#00f5ff', background: 'rgba(0,245,255,0.12)' }}>
          DONE
        </span>
      </div>

      {/* Indicators strip */}
      {Object.keys(indicators).length > 0 && (
        <div className="px-6 py-4 grid grid-cols-3 sm:grid-cols-6 gap-2 border-b" style={{ borderColor: 'rgba(0,245,255,0.1)' }}>
          <IndicatorPill label="RSI"   value={indicators.RSI} />
          <IndicatorPill label="EMA20" value={indicators.EMA20} />
          <IndicatorPill label="EMA50" value={indicators.EMA50} />
          <IndicatorPill label="ATR"   value={indicators.ATR} />
          <IndicatorPill label="MACD"  value={indicators.MACD} />
          <IndicatorPill label="Price" value={indicators.current_price} />
        </div>
      )}

      {/* Analysis text – paragraph stagger */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="px-6 py-5 space-y-3"
      >
        {paragraphs.map((para, i) => (
          <motion.p
            key={i}
            variants={fadeUp}
            className="text-sm leading-relaxed"
            style={{ color: para.startsWith('**') ? 'var(--text-primary)' : 'var(--text-muted)' }}
          >
            {para.replace(/\*\*/g, '')}
          </motion.p>
        ))}
      </motion.div>
    </motion.div>
  )
}
