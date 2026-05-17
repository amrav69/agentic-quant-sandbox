/**
 * Dashboard.jsx  —  Route: /
 * Polished layout pass: consistent page-container, section rhythm,
 * balanced spacing, and all components properly aligned.
 */
import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useScroll, useTransform, useSpring } from 'framer-motion'
import { Cpu, Code2, Shield, ArrowRight, Zap, Activity, Clock, CheckCircle, XCircle } from 'lucide-react'
import PageWrapper   from '../components/layout/PageWrapper'
import AgentCard     from '../components/ui/AgentCard'
import LiveTicker    from '../components/ui/LiveTicker'
import ScrollReveal  from '../components/ui/ScrollReveal'
import PnLChart      from '../components/charts/PnLChart'
import useTypingEffect from '../hooks/useTypingEffect'
import { staggerContainer, fadeUp } from '../components/animations/motionVariants'
import useStore from '../store/useStore'

const AGENTS = [
  { label: 'Research Agent', icon: Cpu,    status: 'ONLINE', accentColor: '#00f5ff', description: 'Reads live indicators and forms a qualitative trade hypothesis with entry/exit logic.' },
  { label: 'CodeGen Agent',  icon: Code2,  status: 'ONLINE', accentColor: '#7c3aed', description: 'Converts the strategy hypothesis into executable vectorbt Python backtest code.' },
  { label: 'Critic Agent',   icon: Shield, status: 'ONLINE', accentColor: '#4f46e5', description: 'Audits generated code for lookahead bias, overfitting, and unrealistic assumptions.' },
]

const FEED_DATA = [
  { id: 1, symbol: 'BTC-USD', verdict: 'FAIL', sharpe:  0.82, time: '2 min ago',  regime: 'Ranging' },
  { id: 2, symbol: 'AAPL',    verdict: 'PASS', sharpe:  1.74, time: '11 min ago', regime: 'Bullish' },
  { id: 3, symbol: 'ETH-USD', verdict: 'FAIL', sharpe: -0.21, time: '28 min ago', regime: 'Bearish' },
  { id: 4, symbol: 'NVDA',    verdict: 'PASS', sharpe:  2.31, time: '47 min ago', regime: 'Bullish' },
  { id: 5, symbol: 'SOL-USD', verdict: 'PASS', sharpe:  1.18, time: '1 hr ago',   regime: 'Ranging' },
]

const STATS = [
  { label: 'Pipeline Agents', value: '3'   },
  { label: 'Supported Assets', value: '∞'  },
  { label: 'Avg Latency',      value: '<5s' },
  { label: 'Risk Checks',      value: '10+' },
]

function Cursor({ done }) {
  return (
    <motion.span
      animate={{ opacity: done ? [1, 0, 1] : 1 }}
      transition={{ duration: 0.9, repeat: done ? Infinity : 0 }}
      style={{
        display: 'inline-block', width: 3, height: '0.85em',
        marginLeft: 4, verticalAlign: 'middle',
        borderRadius: 2, background: 'var(--accent)',
      }}
    />
  )
}

function FeedRow({ symbol, verdict, sharpe, time, regime }) {
  const isPass = verdict === 'PASS'
  const color  = isPass ? '#10b981' : '#ef4444'
  const Icon   = isPass ? CheckCircle : XCircle

  return (
    <motion.div
      variants={fadeUp}
      whileHover={{ x: 4 }}
      transition={{ duration: 0.18 }}
      className="glass rounded-xl flex items-center gap-4 px-5 py-4"
    >
      <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${color}15` }}>
        <Icon size={15} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-mono font-semibold text-[13px]" style={{ color: 'var(--accent)' }}>{symbol}</p>
        <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
          {regime} · Sharpe {sharpe >= 0 ? '+' : ''}{sharpe.toFixed(2)}
        </p>
      </div>
      <span className="shrink-0 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold"
        style={{ color, background: `${color}15` }}>{verdict}</span>
      <div className="hidden sm:flex items-center gap-1 text-[11px] shrink-0" style={{ color: 'var(--text-muted)' }}>
        <Clock size={10} /> {time}
      </div>
    </motion.div>
  )
}

export default function Dashboard() {
  const navigate        = useNavigate()
  const addNotification = useStore((s) => s.addNotification)
  const heroRef         = useRef(null)

  const { displayed, isDone } = useTypingEffect('Autonomous Trading Intelligence', 52, 700)

  const { scrollYProgress } = useScroll({ target: heroRef, offset: ['start start', 'end start'] })
  const rawY  = useTransform(scrollYProgress, [0, 1], ['0%', '32%'])
  const gridY = useSpring(rawY, { stiffness: 80, damping: 22 })

  return (
    <PageWrapper>
      {/* ── HERO ──────────────────────────────────────────────── */}
      <section ref={heroRef} className="relative overflow-hidden" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <motion.div style={{ y: gridY }} className="absolute inset-0 grid-bg opacity-50 pointer-events-none" />

        {/* Ambient orbs */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <motion.div
            animate={{ scale: [1, 1.12, 1], opacity: [0.12, 0.22, 0.12] }}
            transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
            style={{ position: 'absolute', top: '20%', left: '50%', transform: 'translateX(-50%)', width: 560, height: 560, borderRadius: '50%', filter: 'blur(110px)', background: 'radial-gradient(circle, rgba(124,58,237,0.4) 0%, transparent 70%)' }}
          />
          <motion.div
            animate={{ scale: [1, 1.18, 1], opacity: [0.08, 0.16, 0.08] }}
            transition={{ duration: 11, repeat: Infinity, ease: 'easeInOut', delay: 2.5 }}
            style={{ position: 'absolute', top: '30%', left: '25%', width: 380, height: 380, borderRadius: '50%', filter: 'blur(90px)', background: 'radial-gradient(circle, rgba(0,245,255,0.3) 0%, transparent 70%)' }}
          />
        </div>

        {/* Hero content */}
        <div className="page-container relative z-10 flex flex-col items-center justify-center text-center"
          style={{ minHeight: 'calc(100vh - 64px)', paddingTop: '3rem', paddingBottom: '3rem' }}>

          {/* Eyebrow */}
          <motion.div
            initial={{ opacity: 0, scale: 0.88 }} animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="glass inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8"
          >
            <motion.span animate={{ opacity: [1, 0.2, 1] }} transition={{ duration: 1.6, repeat: Infinity }}
              style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block', flexShrink: 0 }} />
            <span className="label-xs" style={{ color: 'var(--accent)' }}>AI Pipeline · Live</span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="gradient-accent-text mb-6"
            style={{ maxWidth: 840 }}
          >
            {displayed}<Cursor done={isDone} />
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.32, duration: 0.55 }}
            style={{ maxWidth: 560, color: 'var(--text-muted)', fontSize: '1.05rem', lineHeight: 1.7, marginBottom: '2.5rem' }}
          >
            An agentic pipeline that autonomously researches market conditions,
            generates backtest code, and critiques strategies with institutional rigor.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.46, duration: 0.5 }}
            className="flex flex-wrap items-center justify-center gap-3 mb-16"
          >
            <motion.button
              whileHover={{ scale: 1.05, boxShadow: '0 0 40px rgba(0,245,255,0.3)' }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/analyze')}
              className="flex items-center gap-2 rounded-xl font-semibold text-[14px]"
              style={{ padding: '0.75rem 1.75rem', background: 'linear-gradient(135deg, #7c3aed, #00f5ff)', color: '#fff' }}
            >
              <Zap size={15} /> Run Pipeline <ArrowRight size={13} />
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => addNotification({ type: 'info', message: 'Explore the Analyze page to run your first pipeline.' })}
              className="glass flex items-center gap-2 rounded-xl text-[14px] font-medium"
              style={{ padding: '0.75rem 1.75rem', color: 'var(--text-muted)' }}
            >
              <Activity size={14} /> View Docs
            </motion.button>
          </motion.div>

          {/* Stat strip */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            transition={{ delay: 0.72, duration: 0.6 }}
            className="flex flex-wrap justify-center gap-10"
          >
            {STATS.map(({ label, value }) => (
              <div key={label} className="text-center">
                <p className="gradient-accent-text font-bold" style={{ fontSize: 'clamp(1.6rem, 4vw, 2.2rem)' }}>{value}</p>
                <p className="label-xs mt-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── LIVE TICKER ───────────────────────────────────────── */}
      <LiveTicker />

      {/* ── MAIN CONTENT ──────────────────────────────────────── */}
      <div className="page-container" style={{ paddingTop: '4rem', paddingBottom: '5rem' }}>

        {/* Agent Grid */}
        <ScrollReveal className="mb-16">
          <div className="flex items-end justify-between mb-6 gap-4">
            <div>
              <p className="label-xs mb-1" style={{ color: 'var(--accent)' }}>Active Agents</p>
              <h2>Pipeline Status</h2>
            </div>
            <motion.button
              whileHover={{ color: 'var(--accent)' }} onClick={() => navigate('/analyze')}
              className="flex items-center gap-1.5 text-[12px] font-mono shrink-0"
              style={{ color: 'var(--text-muted)', transition: 'color 0.2s' }}
            >
              Run Analysis <ArrowRight size={12} />
            </motion.button>
          </div>
          <motion.div
            variants={staggerContainer} initial="hidden" whileInView="visible"
            viewport={{ once: true, margin: '-80px' }}
            className="grid grid-cols-1 md:grid-cols-3 gap-4"
          >
            {AGENTS.map((a) => (
              <AgentCard key={a.label} {...a}
                onClick={() => addNotification({ type: 'info', message: `${a.label} is ${a.status}` })} />
            ))}
          </motion.div>
        </ScrollReveal>

        {/* PnL Chart + Stats */}
        <ScrollReveal delay={0.05} className="mb-16">
          <div className="mb-6">
            <p className="label-xs mb-1" style={{ color: 'var(--accent)' }}>Backtest Performance</p>
            <h2>Simulated PnL Curve</h2>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <PnLChart symbol="BTC-USD (90d backtest)" />
            </div>
            <div className="flex flex-col gap-3">
              {[
                { label: 'Sharpe Ratio', value: '1.74',   color: '#10b981' },
                { label: 'Max Drawdown', value: '-8.3%',  color: '#ef4444' },
                { label: 'Total Return', value: '+31.2%', color: '#10b981' },
                { label: 'Win Rate',     value: '58.4%',  color: '#00f5ff' },
              ].map(({ label, value, color }, i) => (
                <motion.div key={label}
                  initial={{ opacity: 0, x: 18 }} whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.07, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                  whileHover={{ scale: 1.02 }}
                  className="glass rounded-xl flex-1 flex flex-col justify-center"
                  style={{ padding: '1.1rem 1.4rem', minHeight: 72 }}
                >
                  <p className="label-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>{label}</p>
                  <p className="font-mono font-bold" style={{ color, fontSize: '1.55rem' }}>{value}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </ScrollReveal>

        {/* Analysis Feed */}
        <ScrollReveal delay={0.05}>
          <div className="flex items-end justify-between mb-6 gap-4">
            <div>
              <p className="label-xs mb-1" style={{ color: 'var(--accent)' }}>Pipeline History</p>
              <h2>Recent Analyses</h2>
            </div>
            <motion.button
              whileHover={{ color: 'var(--accent)' }} onClick={() => navigate('/history')}
              className="flex items-center gap-1.5 text-[12px] font-mono shrink-0"
              style={{ color: 'var(--text-muted)', transition: 'color 0.2s' }}
            >
              View All <ArrowRight size={12} />
            </motion.button>
          </div>
          <motion.div
            variants={staggerContainer} initial="hidden" whileInView="visible"
            viewport={{ once: true, margin: '-60px' }}
            className="flex flex-col gap-2.5"
          >
            {FEED_DATA.map((row) => <FeedRow key={row.id} {...row} />)}
          </motion.div>
        </ScrollReveal>
      </div>
    </PageWrapper>
  )
}
