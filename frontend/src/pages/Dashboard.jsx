/**
 * Dashboard.jsx  —  Route: /
 *
 * Sections (top → bottom):
 *  1. Hero        – typing headline, parallax grid, CTA buttons
 *  2. LiveTicker  – infinite marquee
 *  3. Agent Grid  – AgentCard × 3
 *  4. PnL Chart   – Recharts animated area chart
 *  5. Analysis Feed – recent pipeline run rows
 */
import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
} from 'framer-motion'
import { Cpu, Code2, Shield, ArrowRight, Zap, Activity, Clock, CheckCircle, XCircle } from 'lucide-react'

import PageWrapper   from '../components/layout/PageWrapper'
import AgentCard     from '../components/ui/AgentCard'
import LiveTicker    from '../components/ui/LiveTicker'
import ScrollReveal  from '../components/ui/ScrollReveal'
import PnLChart      from '../components/charts/PnLChart'
import useTypingEffect from '../hooks/useTypingEffect'
import { staggerContainer, fadeUp } from '../components/animations/motionVariants'
import useStore from '../store/useStore'

/* ─── Static Data ─────────────────────────────────────────────────────────── */
const AGENTS = [
  {
    label:       'Research Agent',
    icon:        Cpu,
    status:      'ONLINE',
    accentColor: '#00f5ff',
    description: 'Reads live indicators and forms a qualitative trade hypothesis with entry/exit logic.',
  },
  {
    label:       'CodeGen Agent',
    icon:        Code2,
    status:      'ONLINE',
    accentColor: '#7c3aed',
    description: 'Converts the strategy hypothesis into executable vectorbt Python backtest code.',
  },
  {
    label:       'Critic Agent',
    icon:        Shield,
    status:      'ONLINE',
    accentColor: '#4f46e5',
    description: 'Audits generated code for lookahead bias, overfitting, and unrealistic assumptions.',
  },
]

const FEED_DATA = [
  { id: 1, symbol: 'BTC-USD',  verdict: 'FAIL', sharpe:  0.82, time: '2 min ago',  regime: 'Ranging' },
  { id: 2, symbol: 'AAPL',     verdict: 'PASS', sharpe:  1.74, time: '11 min ago', regime: 'Bullish' },
  { id: 3, symbol: 'ETH-USD',  verdict: 'FAIL', sharpe: -0.21, time: '28 min ago', regime: 'Bearish' },
  { id: 4, symbol: 'NVDA',     verdict: 'PASS', sharpe:  2.31, time: '47 min ago', regime: 'Bullish' },
  { id: 5, symbol: 'SOL-USD',  verdict: 'PASS', sharpe:  1.18, time: '1 hr ago',   regime: 'Ranging' },
]

/* ─── Sub-components ──────────────────────────────────────────────────────── */

/** Blinking cursor shown at end of typing text */
function Cursor({ done }) {
  return (
    <motion.span
      animate={{ opacity: done ? [1, 0, 1] : 1 }}
      transition={{ duration: 0.9, repeat: done ? Infinity : 0 }}
      className="inline-block w-[3px] h-[1em] ml-1 align-middle rounded-sm"
      style={{ background: 'var(--accent)' }}
    />
  )
}

/** Single row in the Recent Analysis Feed */
function FeedRow({ symbol, verdict, sharpe, time, regime, index }) {
  const isPass   = verdict === 'PASS'
  const color    = isPass ? '#10b981' : '#ef4444'
  const Icon     = isPass ? CheckCircle : XCircle

  return (
    <motion.div
      variants={fadeUp}
      whileHover={{ x: 4, backgroundColor: 'rgba(255,255,255,0.025)' }}
      transition={{ duration: 0.2 }}
      className="glass rounded-xl px-5 py-4 flex items-center gap-4 cursor-default"
      style={{ border: '1px solid var(--border-glass)' }}
    >
      {/* Verdict icon */}
      <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: `${color}18` }}>
        <Icon size={16} style={{ color }} />
      </div>

      {/* Symbol + regime */}
      <div className="flex-1 min-w-0">
        <p className="font-mono font-semibold text-sm" style={{ color: 'var(--accent)' }}>
          {symbol}
        </p>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
          {regime} · Sharpe {sharpe >= 0 ? '+' : ''}{sharpe.toFixed(2)}
        </p>
      </div>

      {/* Verdict badge */}
      <span
        className="shrink-0 px-3 py-1 rounded-full text-[11px] font-mono font-semibold tracking-wide"
        style={{ color, background: `${color}18` }}
      >
        {verdict}
      </span>

      {/* Time */}
      <div className="shrink-0 flex items-center gap-1.5 text-xs"
        style={{ color: 'var(--text-muted)' }}>
        <Clock size={11} />
        {time}
      </div>
    </motion.div>
  )
}

/* ─── Dashboard Page ──────────────────────────────────────────────────────── */
export default function Dashboard() {
  const navigate         = useNavigate()
  const addNotification  = useStore((s) => s.addNotification)
  const heroRef          = useRef(null)

  // Typing headline
  const { displayed, isDone } = useTypingEffect('Autonomous Trading Intelligence', 52, 600)

  // Parallax scroll for hero grid
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ['start start', 'end start'] })
  const rawY  = useTransform(scrollYProgress, [0, 1], ['0%', '35%'])
  const gridY = useSpring(rawY, { stiffness: 80, damping: 20 })

  return (
    <PageWrapper>
      {/* ════════════════════════════════════════════════════════════════
          1. HERO SECTION
      ════════════════════════════════════════════════════════════════ */}
      <section
        ref={heroRef}
        className="relative min-h-[92vh] flex flex-col justify-center overflow-hidden"
      >
        {/* Parallax ambient grid */}
        <motion.div
          style={{ y: gridY }}
          className="absolute inset-0 grid-bg opacity-60 pointer-events-none"
        />

        {/* Radial glow orbs */}
        <div className="absolute inset-0 pointer-events-none">
          <motion.div
            animate={{ scale: [1, 1.15, 1], opacity: [0.15, 0.25, 0.15] }}
            transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full blur-[120px]"
            style={{ background: 'radial-gradient(circle, #7c3aed40 0%, transparent 70%)' }}
          />
          <motion.div
            animate={{ scale: [1, 1.2, 1], opacity: [0.1, 0.18, 0.1] }}
            transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
            className="absolute top-1/3 left-1/4 w-[400px] h-[400px] rounded-full blur-[100px]"
            style={{ background: 'radial-gradient(circle, #00f5ff30 0%, transparent 70%)' }}
          />
        </div>

        {/* Hero Content */}
        <div className="relative z-10 max-w-screen-xl mx-auto px-6 pt-24 pb-16 text-center">

          {/* Eyebrow badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex items-center gap-2 glass px-4 py-1.5 rounded-full mb-8"
          >
            <motion.span
              animate={{ opacity: [1, 0.2, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: 'var(--accent)' }}
            />
            <span className="text-xs font-mono tracking-widest uppercase"
              style={{ color: 'var(--accent)' }}>
              AI Pipeline · Live
            </span>
          </motion.div>

          {/* Typing headline */}
          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="text-5xl sm:text-6xl lg:text-7xl font-bold leading-tight mb-6"
          >
            <span className="gradient-accent-text">
              {displayed}
              <Cursor done={isDone} />
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.55 }}
            className="text-base sm:text-lg max-w-2xl mx-auto leading-relaxed mb-10"
            style={{ color: 'var(--text-muted)' }}
          >
            An agentic pipeline that autonomously researches market conditions,
            generates backtest code, and critiques strategies with institutional rigor.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="flex flex-wrap items-center justify-center gap-4"
          >
            <motion.button
              whileHover={{ scale: 1.05, boxShadow: '0 0 40px rgba(0,245,255,0.35)' }}
              whileTap={{ scale: 0.97 }}
              onClick={() => navigate('/analyze')}
              className="flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-sm"
              style={{
                background: 'linear-gradient(135deg, #7c3aed, #00f5ff)',
                color: '#fff',
              }}
            >
              <Zap size={15} />
              Run Pipeline
              <ArrowRight size={14} />
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.04, borderColor: 'var(--accent)' }}
              whileTap={{ scale: 0.97 }}
              onClick={() => addNotification({ type: 'info', message: 'Explore the Analyze page to run your first pipeline.' })}
              className="flex items-center gap-2 px-7 py-3.5 rounded-xl text-sm font-medium glass"
              style={{ color: 'var(--text-muted)', border: '1px solid var(--border-glass)', transition: 'border-color 0.3s' }}
            >
              <Activity size={14} />
              View Docs
            </motion.button>
          </motion.div>

          {/* Stat strip */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8, duration: 0.6 }}
            className="flex flex-wrap justify-center gap-8 mt-14"
          >
            {[
              { label: 'Pipeline Agents', value: '3' },
              { label: 'Supported Assets', value: '∞' },
              { label: 'Avg Latency',     value: '<5s' },
              { label: 'Risk Checks',     value: '10+' },
            ].map(({ label, value }) => (
              <div key={label} className="text-center">
                <p className="text-3xl font-bold gradient-accent-text">{value}</p>
                <p className="text-xs mt-1 tracking-widest uppercase"
                  style={{ color: 'var(--text-muted)' }}>{label}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ════════════════════════════════════════════════════════════════
          2. LIVE TICKER
      ════════════════════════════════════════════════════════════════ */}
      <LiveTicker />

      {/* Remaining sections */}
      <div className="max-w-screen-xl mx-auto px-6 py-16 space-y-20">

        {/* ════════════════════════════════════════════════════════════════
            3. AGENT STATUS GRID
        ════════════════════════════════════════════════════════════════ */}
        <ScrollReveal>
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] mb-1"
                style={{ color: 'var(--accent)' }}>Active Agents</p>
              <h2 className="text-2xl font-bold">Pipeline Status</h2>
            </div>
            <motion.button
              whileHover={{ scale: 1.04, color: 'var(--accent)' }}
              onClick={() => navigate('/analyze')}
              className="flex items-center gap-1.5 text-xs font-mono"
              style={{ color: 'var(--text-muted)', transition: 'color 0.2s' }}
            >
              Run Analysis <ArrowRight size={12} />
            </motion.button>
          </div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-80px' }}
            className="grid grid-cols-1 md:grid-cols-3 gap-5"
          >
            {AGENTS.map((agent) => (
              <AgentCard
                key={agent.label}
                {...agent}
                onClick={() => addNotification({ type: 'info', message: `${agent.label} is ${agent.status}` })}
              />
            ))}
          </motion.div>
        </ScrollReveal>

        {/* ════════════════════════════════════════════════════════════════
            4. PnL CHART
        ════════════════════════════════════════════════════════════════ */}
        <ScrollReveal delay={0.05}>
          <div className="mb-6">
            <p className="text-xs uppercase tracking-[0.3em] mb-1"
              style={{ color: 'var(--accent)' }}>Backtest Performance</p>
            <h2 className="text-2xl font-bold">Simulated PnL Curve</h2>
          </div>

          {/* Two-column layout: big chart + mini stats */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Chart – takes 2 cols */}
            <div className="lg:col-span-2">
              <PnLChart symbol="BTC-USD (90d backtest)" />
            </div>

            {/* Mini stat cards */}
            <div className="flex flex-col gap-4">
              {[
                { label: 'Sharpe Ratio',   value: '1.74',   color: '#10b981', good: true  },
                { label: 'Max Drawdown',   value: '-8.3%',  color: '#ef4444', good: false },
                { label: 'Total Return',   value: '+31.2%', color: '#10b981', good: true  },
                { label: 'Win Rate',       value: '58.4%',  color: '#00f5ff', good: true  },
              ].map(({ label, value, color, good }, i) => (
                <motion.div
                  key={label}
                  initial={{ opacity: 0, x: 20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                  whileHover={{ scale: 1.02, borderColor: color }}
                  className="glass rounded-xl px-5 py-4 flex-1"
                  style={{ border: '1px solid var(--border-glass)', transition: 'border-color 0.3s' }}
                >
                  <p className="text-xs uppercase tracking-widest mb-2"
                    style={{ color: 'var(--text-muted)' }}>{label}</p>
                  <p className="font-mono text-2xl font-bold" style={{ color }}>
                    {value}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </ScrollReveal>

        {/* ════════════════════════════════════════════════════════════════
            5. RECENT ANALYSIS FEED
        ════════════════════════════════════════════════════════════════ */}
        <ScrollReveal delay={0.05}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] mb-1"
                style={{ color: 'var(--accent)' }}>Pipeline History</p>
              <h2 className="text-2xl font-bold">Recent Analyses</h2>
            </div>
            <motion.button
              whileHover={{ scale: 1.04, color: 'var(--accent)' }}
              onClick={() => navigate('/history')}
              className="flex items-center gap-1.5 text-xs font-mono"
              style={{ color: 'var(--text-muted)', transition: 'color 0.2s' }}
            >
              View All <ArrowRight size={12} />
            </motion.button>
          </div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-60px' }}
            className="space-y-3"
          >
            {FEED_DATA.map((row, i) => (
              <FeedRow key={row.id} {...row} index={i} />
            ))}
          </motion.div>
        </ScrollReveal>

      </div>

      {/* Bottom spacer */}
      <div className="h-20" />
    </PageWrapper>
  )
}
