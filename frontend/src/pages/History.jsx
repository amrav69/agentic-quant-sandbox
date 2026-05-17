/**
 * History.jsx  —  Route: /history
 *
 * Features:
 *  1. Filter tabs: ALL / PASS / FAIL  (animated morphing pill)
 *  2. Staggered glass table rows
 *  3. Expandable rows with Research / Code / Critic tabs
 *  4. Empty state with floating animation
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  History as HistoryIcon, CheckCircle, XCircle, Clock,
  ChevronDown, Cpu, Code2, Shield, Trash2, BarChart2,
} from 'lucide-react'
import PageWrapper from '../components/layout/PageWrapper'
import CodeBlock   from '../components/ui/CodeBlock'
import { staggerContainer, fadeUp } from '../components/animations/motionVariants'
import useStore from '../store/useStore'

/* ─── Helpers ────────────────────────────────────────────────────────── */
function formatTime(iso) {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60)    return `${diff}s ago`
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function stripFences(code = '') {
  return code.replace(/^```[\w]*\n?/, '').replace(/\n?```$/, '').trim()
}

/* ─── Filter Tabs ────────────────────────────────────────────────────── */
const TABS = ['ALL', 'PASS', 'FAIL']

function FilterTabs({ active, onChange }) {
  return (
    <div className="inline-flex items-center glass rounded-xl p-1 gap-1">
      {TABS.map((tab) => {
        const isActive = active === tab
        const color = tab === 'PASS' ? '#10b981' : tab === 'FAIL' ? '#ef4444' : 'var(--accent)'
        return (
          <button key={tab} onClick={() => onChange(tab)} className="relative px-5 py-2 rounded-lg text-xs font-mono font-semibold tracking-widest transition-colors">
            {isActive && (
              <motion.span
                layoutId="filter-pill"
                className="absolute inset-0 rounded-lg"
                style={{ background: `${color}18`, border: `1px solid ${color}40` }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative z-10" style={{ color: isActive ? color : 'var(--text-muted)' }}>
              {tab}
            </span>
          </button>
        )
      })}
    </div>
  )
}

/* ─── Verdict Badge ──────────────────────────────────────────────────── */
function VerdictBadge({ verdict }) {
  const isPass = verdict === 'PASS'
  const color  = isPass ? '#10b981' : '#ef4444'
  const Icon   = isPass ? CheckCircle : XCircle
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-semibold"
      style={{ color, background: `${color}18`, border: `1px solid ${color}30` }}>
      <Icon size={11} /> {verdict}
    </span>
  )
}

/* ─── Expanded Content Tabs ──────────────────────────────────────────── */
const CONTENT_TABS = [
  { key: 'research', label: 'Research',  icon: Cpu,    color: '#00f5ff' },
  { key: 'code',     label: 'Code',      icon: Code2,  color: '#7c3aed' },
  { key: 'critique', label: 'Critique',  icon: Shield, color: '#4f46e5' },
]

function ExpandedContent({ entry }) {
  const [tab, setTab] = useState('research')
  const cfg = CONTENT_TABS.find((t) => t.key === tab)

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="overflow-hidden"
    >
      <div className="border-t pt-4 pb-2 mt-2" style={{ borderColor: 'var(--border-glass)' }}>
        {/* Sub-tabs */}
        <div className="flex gap-2 mb-4">
          {CONTENT_TABS.map(({ key, label, icon: Icon, color }) => {
            const active = tab === key
            return (
              <motion.button
                key={key}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => setTab(key)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-colors"
                style={{
                  color:      active ? color : 'var(--text-muted)',
                  background: active ? `${color}15` : 'transparent',
                  border:     `1px solid ${active ? `${color}40` : 'transparent'}`,
                }}
              >
                <Icon size={12} /> {label}
              </motion.button>
            )
          })}
        </div>

        {/* Tab content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.22 }}
          >
            {/* Research */}
            {tab === 'research' && (
              <div className="space-y-4">
                {/* Indicator pills */}
                {entry.indicators && Object.keys(entry.indicators).length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(entry.indicators).map(([k, v]) => (
                      <span key={k} className="px-2.5 py-1 rounded-lg text-[11px] font-mono glass"
                        style={{ color: 'var(--accent)', border: '1px solid var(--border-glass)' }}>
                        {k}: {typeof v === 'number' ? v.toFixed(2) : v}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                  {entry.research?.analysis || 'No research data available.'}
                </p>
              </div>
            )}

            {/* Code */}
            {tab === 'code' && (
              <CodeBlock
                code={stripFences(entry.code?.code ?? '')}
                language="python"
                title={`${entry.symbol}_backtest.py`}
                maxHeight="300px"
              />
            )}

            {/* Critique */}
            {tab === 'critique' && entry.critique && (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <VerdictBadge verdict={entry.critique.verdict} />
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {(entry.critique.issues ?? []).length} issues · {(entry.critique.suggestions ?? []).length} suggestions
                  </span>
                </div>
                {/* Issues */}
                {(entry.critique.issues ?? []).length > 0 && (
                  <div>
                    <p className="text-[10px] uppercase tracking-widest mb-2" style={{ color: '#f59e0b' }}>Issues</p>
                    <ul className="space-y-1.5">
                      {entry.critique.issues.map((iss, i) => (
                        <li key={i} className="text-xs py-2 px-3 rounded-lg flex gap-2"
                          style={{ background: 'rgba(239,68,68,0.06)', color: 'var(--text-muted)' }}>
                          <span style={{ color: '#ef4444' }}>{i + 1}.</span> {iss}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* Suggestions */}
                {(entry.critique.suggestions ?? []).length > 0 && (
                  <div>
                    <p className="text-[10px] uppercase tracking-widest mb-2" style={{ color: '#10b981' }}>Suggestions</p>
                    <ul className="space-y-1.5">
                      {entry.critique.suggestions.map((s, i) => (
                        <li key={i} className="text-xs py-2 px-3 rounded-lg flex gap-2"
                          style={{ background: 'rgba(16,185,129,0.06)', color: 'var(--text-muted)' }}>
                          <span style={{ color: '#10b981' }}>→</span> {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

/* ─── History Row ────────────────────────────────────────────────────── */
function HistoryRow({ entry }) {
  const [open, setOpen] = useState(false)

  return (
    <motion.div
      variants={fadeUp}
      layout
      className="glass rounded-xl overflow-hidden cursor-pointer"
      style={{ border: '1px solid var(--border-glass)' }}
      whileHover={{ borderColor: open ? 'var(--border-glass)' : 'rgba(0,245,255,0.15)' }}
      transition={{ duration: 0.2 }}
    >
      {/* Row header — click to toggle */}
      <div
        className="flex items-center gap-4 px-5 py-4"
        onClick={() => setOpen((v) => !v)}
      >
        {/* Symbol */}
        <div className="flex-1 min-w-0">
          <p className="font-mono font-semibold text-sm" style={{ color: 'var(--accent)' }}>
            {entry.symbol}
          </p>
          <p className="text-[11px] mt-0.5 font-mono" style={{ color: 'var(--text-muted)' }}>
            {entry.regime ?? 'Live'}
          </p>
        </div>

        {/* Verdict */}
        <VerdictBadge verdict={entry.verdict} />

        {/* Sharpe */}
        {entry.sharpe != null && (
          <div className="hidden sm:flex items-center gap-1.5 text-xs font-mono"
            style={{ color: entry.sharpe >= 1 ? '#10b981' : 'var(--text-muted)' }}>
            <BarChart2 size={12} />
            {entry.sharpe >= 0 ? '+' : ''}{entry.sharpe.toFixed(2)}
          </div>
        )}

        {/* Time */}
        <div className="hidden md:flex items-center gap-1.5 text-xs"
          style={{ color: 'var(--text-muted)' }}>
          <Clock size={11} />
          {formatTime(entry.timestamp)}
        </div>

        {/* Expand chevron */}
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.25 }}
          style={{ color: 'var(--text-muted)' }}
        >
          <ChevronDown size={16} />
        </motion.div>
      </div>

      {/* Expandable content */}
      <AnimatePresence>
        {open && (
          <div className="px-5 pb-5">
            <ExpandedContent entry={entry} />
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

/* ─── Empty State ────────────────────────────────────────────────────── */
function EmptyState({ filter }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      className="text-center py-24"
    >
      <motion.div
        animate={{ y: [-6, 6, -6] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
        className="w-20 h-20 mx-auto mb-6 rounded-2xl flex items-center justify-center"
        style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.15), rgba(0,245,255,0.1))', border: '1px solid var(--border-glass)' }}
      >
        <HistoryIcon size={32} style={{ color: 'var(--accent)' }} />
      </motion.div>
      <p className="font-semibold text-lg mb-2">
        {filter === 'ALL' ? 'No analysis history yet' : `No ${filter} results`}
      </p>
      <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
        {filter === 'ALL'
          ? 'Run a pipeline on the Analyze page to see results here.'
          : `No ${filter.toLowerCase()} verdicts found. Try a different filter.`}
      </p>
    </motion.div>
  )
}

/* ─── History Page ────────────────────────────────────────────────────── */
export default function History() {
  const [filter, setFilter]  = useState('ALL')
  const { analysisHistory, clearHistory } = useStore()

  const filtered = filter === 'ALL'
    ? analysisHistory
    : analysisHistory.filter((e) => e.verdict === filter)

  const passCount = analysisHistory.filter((e) => e.verdict === 'PASS').length
  const failCount = analysisHistory.filter((e) => e.verdict === 'FAIL').length

  return (
    <PageWrapper>
      <div className="max-w-screen-lg mx-auto px-6 pt-12 pb-20">

        {/* ── Header ── */}
        <motion.div
          variants={staggerContainer} initial="hidden" animate="visible"
          className="mb-10"
        >
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-[0.3em] mb-2"
            style={{ color: 'var(--accent)' }}>
            Pipeline History
          </motion.p>
          <motion.div variants={fadeUp} className="flex items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold mb-1">Analysis Archive</h1>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {analysisHistory.length} total runs · {passCount} passed · {failCount} failed
              </p>
            </div>
            {analysisHistory.length > 0 && (
              <motion.button
                whileHover={{ scale: 1.04, color: '#ef4444' }}
                whileTap={{ scale: 0.96 }}
                onClick={clearHistory}
                className="flex items-center gap-2 text-xs font-mono glass px-3 py-2 rounded-lg shrink-0"
                style={{ color: 'var(--text-muted)', border: '1px solid var(--border-glass)', transition: 'color 0.2s' }}
              >
                <Trash2 size={12} /> Clear All
              </motion.button>
            )}
          </motion.div>
        </motion.div>

        {/* ── Stat strip ── */}
        {analysisHistory.length > 0 && (
          <motion.div
            variants={staggerContainer} initial="hidden" animate="visible"
            className="grid grid-cols-3 gap-4 mb-8"
          >
            {[
              { label: 'Total Runs',  value: analysisHistory.length, color: 'var(--accent)' },
              { label: 'Pass Rate',   value: `${analysisHistory.length ? Math.round((passCount / analysisHistory.length) * 100) : 0}%`, color: '#10b981' },
              { label: 'Failed',      value: failCount, color: '#ef4444' },
            ].map(({ label, value, color }) => (
              <motion.div
                key={label} variants={fadeUp}
                className="glass rounded-xl px-5 py-4"
              >
                <p className="text-xs uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>{label}</p>
                <p className="font-mono text-2xl font-bold" style={{ color }}>{value}</p>
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* ── Filter Tabs ── */}
        <div className="flex items-center justify-between mb-6">
          <FilterTabs active={filter} onChange={setFilter} />
          <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {filtered.length} result{filtered.length !== 1 ? 's' : ''}
          </p>
        </div>

        {/* ── Rows ── */}
        <AnimatePresence mode="wait">
          {filtered.length === 0 ? (
            <EmptyState key="empty" filter={filter} />
          ) : (
            <motion.div
              key={filter}
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              {filtered.map((entry) => (
                <HistoryRow key={entry.id} entry={entry} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageWrapper>
  )
}
