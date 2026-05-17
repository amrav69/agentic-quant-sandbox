/**
 * Analyze.jsx  —  Route: /analyze
 *
 * Core AI pipeline visualization interface.
 *
 * Flow:
 *  1. User enters symbol → clicks Run Analysis
 *  2. GET /analyze/{symbol} → Research step revealed
 *  3. POST /critique (built from indicators) → CodeGen + Critic revealed sequentially
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Zap, Cpu, Code2, Shield, CheckCircle, Loader2, AlertCircle } from 'lucide-react'
import PageWrapper    from '../components/layout/PageWrapper'
import ResearchPanel  from '../components/agents/ResearchPanel'
import CodeGenPanel   from '../components/agents/CodeGenPanel'
import CriticPanel    from '../components/agents/CriticPanel'
import { SkeletonCard } from '../components/ui/LoadingSkeleton'
import { staggerContainer, fadeUp } from '../components/animations/motionVariants'
import { analyzeSymbol, critiqueStrategy } from '../services/apiClient'
import useStore from '../store/useStore'

/* ─── Pipeline step definitions ─────────────────────────────────────────── */
const STEPS = [
  { key: 'research', label: 'Research',  icon: Cpu,    color: '#00f5ff' },
  { key: 'codegen',  label: 'CodeGen',   icon: Code2,  color: '#7c3aed' },
  { key: 'critic',   label: 'Critique',  icon: Shield, color: '#4f46e5' },
]

/* ─── Pipeline Stepper ──────────────────────────────────────────────────── */
function PipelineStepper({ activeStep, doneSteps }) {
  return (
    <div className="flex items-center justify-center gap-0 mb-10">
      {STEPS.map((step, i) => {
        const isDone    = doneSteps.includes(step.key)
        const isActive  = activeStep === step.key
        const Icon      = step.icon
        const color     = isDone || isActive ? step.color : 'var(--text-muted)'

        return (
          <div key={step.key} className="flex items-center">
            <motion.div
              animate={{ borderColor: isActive || isDone ? step.color : 'rgba(255,255,255,0.1)' }}
              transition={{ duration: 0.4 }}
              className="flex flex-col items-center gap-1.5"
            >
              <motion.div
                animate={{
                  background: isActive ? `${step.color}25` : isDone ? `${step.color}18` : 'rgba(255,255,255,0.04)',
                  borderColor: isActive || isDone ? step.color : 'rgba(255,255,255,0.1)',
                  boxShadow: isActive ? `0 0 20px ${step.color}40` : 'none',
                }}
                transition={{ duration: 0.4 }}
                className="w-10 h-10 rounded-full flex items-center justify-center border"
              >
                {isActive ? (
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                    <Loader2 size={16} style={{ color }} />
                  </motion.div>
                ) : isDone ? (
                  <CheckCircle size={16} style={{ color }} />
                ) : (
                  <Icon size={16} style={{ color: 'var(--text-muted)' }} />
                )}
              </motion.div>
              <p className="text-[10px] uppercase tracking-widest font-mono" style={{ color }}>
                {step.label}
              </p>
            </motion.div>

            {/* Connector line (not after last item) */}
            {i < STEPS.length - 1 && (
              <motion.div
                animate={{ background: doneSteps.includes(step.key) ? step.color : 'rgba(255,255,255,0.08)' }}
                transition={{ duration: 0.6 }}
                className="w-16 sm:w-24 h-px mx-3 mb-4"
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ─── Analyze Page ─────────────────────────────────────────────────────── */
export default function Analyze() {
  const [inputVal,   setInputVal]   = useState('')
  const [error,      setError]      = useState(null)
  const [doneSteps,  setDoneSteps]  = useState([])

  const {
    activeTicker, setActiveTicker, addRecentTicker,
    isLoading, setIsLoading,
    activeStep, setActiveStep,
    liveIndicators,  setLiveIndicators,
    researchResult,  setResearchResult,
    generatedCode,   setGeneratedCode,
    critiqueResult,  setCritiqueResult,
    clearAnalysis,
    addHistoryEntry,
    addNotification,
  } = useStore()

  const handleRun = async () => {
    const symbol = (inputVal.trim() || activeTicker).toUpperCase()
    if (!symbol) return

    // Reset previous results
    clearAnalysis()
    setDoneSteps([])
    setError(null)
    setActiveTicker(symbol)
    addRecentTicker(symbol)
    setIsLoading(true)

    try {
      /* ── Step 1: Research (GET /analyze/{symbol}) ── */
      setActiveStep('research')
      const res1 = await analyzeSymbol(symbol)
      const { live_indicators, ai_analysis } = res1.data
      setLiveIndicators(live_indicators)
      setResearchResult({ analysis: ai_analysis, raw_data: { symbol } })
      setDoneSteps((d) => [...d, 'research'])

      /* ── Build payload for critique from indicators ── */
      const ind = live_indicators ?? {}
      const ema20 = ind.EMA20 ?? 0
      const ema50 = ind.EMA50 ?? 0
      const payload = {
        symbol,
        price:        ind.current_price ?? 0,
        rsi:          ind.RSI ?? 0,
        macd:         `Line: ${(ind.MACD ?? 0).toFixed(4)}, Signal: ${(ind.MACD_signal ?? 0).toFixed(4)}`,
        volume_trend: `EMA20: ${ema20.toFixed(2)} | EMA50: ${ema50.toFixed(2)} | ATR: ${(ind.ATR ?? 0).toFixed(4)} | Trend: ${ema20 > ema50 ? 'Bullish' : 'Bearish'}`,
      }

      /* ── Step 2+3: CodeGen + Critic (POST /critique) ── */
      setActiveStep('codegen')
      const res2 = await critiqueStrategy(payload)
      const { generated_code, critique } = res2.data
      setGeneratedCode(generated_code)
      setDoneSteps((d) => [...d, 'codegen'])

      // Brief pause before showing critic for cinematic effect
      await new Promise((r) => setTimeout(r, 700))
      setActiveStep('critic')
      setCritiqueResult(critique)
      setDoneSteps((d) => [...d, 'critic'])
      setActiveStep(null)

      // Save completed run to history
      addHistoryEntry({
        symbol,
        verdict:    critique?.verdict ?? 'FAIL',
        sharpe:     null,
        regime:     'Live',
        research:   { analysis: researchResult?.analysis ?? '', indicators: live_indicators ?? {} },
        code:       generated_code,
        critique,
        indicators: live_indicators ?? {},
      })
      addNotification({ type: critique?.verdict === 'PASS' ? 'success' : 'info', message: `${symbol} pipeline complete · Verdict: ${critique?.verdict ?? '—'}` })

    } catch (err) {
      setError(err.message ?? 'Pipeline failed. Is the backend running?')
      addNotification({ type: 'error', message: `Pipeline error: ${err.message}` })
    } finally {
      setIsLoading(false)
      setActiveStep(null)
    }
  }

  const hasResults = researchResult || generatedCode || critiqueResult
  const isPipRunning = isLoading

  return (
    <PageWrapper>
      <div className="max-w-screen-lg mx-auto px-6 pt-12 pb-20">

        {/* ── Page Header ── */}
        <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="mb-10">
          <motion.p variants={fadeUp} className="text-xs uppercase tracking-[0.3em] mb-2" style={{ color: 'var(--accent)' }}>
            AI Pipeline
          </motion.p>
          <motion.h1 variants={fadeUp} className="text-3xl font-bold mb-2">Strategy Analyzer</motion.h1>
          <motion.p variants={fadeUp} className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Enter any ticker to run the full Research → CodeGen → Critic pipeline.
          </motion.p>
        </motion.div>

        {/* ── Symbol Input ── */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="glass rounded-2xl p-6 mb-8"
        >
          <label className="block text-xs uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)' }}>
            Ticker Symbol
          </label>
          <div className="flex gap-3">
            {/* Input */}
            <motion.div
              className="flex-1 flex items-center gap-3 rounded-xl px-4 py-3"
              whileFocusWithin={{ boxShadow: '0 0 0 2px rgba(0,245,255,0.4), 0 0 20px rgba(0,245,255,0.15)' }}
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-glass)' }}
            >
              <Search size={16} style={{ color: 'var(--text-muted)' }} />
              <input
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && !isPipRunning && handleRun()}
                placeholder={activeTicker || 'BTC-USD, AAPL, ETH-USD…'}
                disabled={isPipRunning}
                className="flex-1 bg-transparent outline-none font-mono text-base disabled:opacity-50"
                style={{ color: 'var(--accent)', caretColor: 'var(--accent)' }}
              />
            </motion.div>

            {/* Run button */}
            <motion.button
              whileHover={!isPipRunning ? { scale: 1.04, boxShadow: '0 0 30px rgba(0,245,255,0.3)' } : {}}
              whileTap={!isPipRunning ? { scale: 0.97 } : {}}
              onClick={handleRun}
              disabled={isPipRunning}
              className="flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm shrink-0 disabled:opacity-60"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #00f5ff)', color: '#fff' }}
            >
              {isPipRunning ? (
                <motion.div animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}>
                  <Loader2 size={16} />
                </motion.div>
              ) : (
                <Zap size={16} />
              )}
              {isPipRunning ? 'Running…' : 'Run Analysis'}
            </motion.button>
          </div>

          {/* Suggested tickers */}
          <div className="flex gap-2 mt-4 flex-wrap">
            {['BTC-USD', 'ETH-USD', 'AAPL', 'NVDA', 'SOL-USD'].map((t) => (
              <motion.button
                key={t}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => { setInputVal(t); setActiveTicker(t) }}
                disabled={isPipRunning}
                className="text-xs font-mono px-3 py-1 rounded-lg glass disabled:opacity-40"
                style={{ color: 'var(--text-muted)', border: '1px solid var(--border-glass)' }}
              >
                {t}
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* ── Error ── */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="flex items-start gap-3 glass rounded-xl px-5 py-4 mb-6"
              style={{ border: '1px solid rgba(239,68,68,0.35)', background: 'rgba(239,68,68,0.06)' }}
            >
              <AlertCircle size={16} style={{ color: '#ef4444' }} className="mt-0.5 shrink-0" />
              <p className="text-sm" style={{ color: '#ef4444' }}>{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Pipeline Stepper ── */}
        <AnimatePresence>
          {(isPipRunning || hasResults) && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <PipelineStepper activeStep={activeStep} doneSteps={doneSteps} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Pipeline Results ── */}
        <AnimatePresence mode="wait">
          <motion.div className="space-y-6">

            {/* Step 1: Research */}
            <AnimatePresence>
              {activeStep === 'research' && !researchResult && (
                <motion.div key="research-skel" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <SkeletonCard lines={5} />
                </motion.div>
              )}
              {researchResult && (
                <motion.div key="research-done" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <ResearchPanel
                    analysisText={researchResult.analysis ?? ''}
                    indicators={liveIndicators ?? {}}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Step 2: CodeGen */}
            <AnimatePresence>
              {activeStep === 'codegen' && !generatedCode && (
                <motion.div key="codegen-skel" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <SkeletonCard lines={8} />
                </motion.div>
              )}
              {generatedCode && (
                <motion.div key="codegen-done" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <CodeGenPanel code={generatedCode.code ?? ''} />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Step 3: Critic */}
            <AnimatePresence>
              {activeStep === 'critic' && !critiqueResult && (
                <motion.div key="critic-skel" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <SkeletonCard lines={6} />
                </motion.div>
              )}
              {critiqueResult && (
                <motion.div key="critic-done" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <CriticPanel
                    verdict={critiqueResult.verdict}
                    issues={critiqueResult.issues ?? []}
                    suggestions={critiqueResult.suggestions ?? []}
                  />
                </motion.div>
              )}
            </AnimatePresence>

          </motion.div>
        </AnimatePresence>

        {/* Empty state */}
        {!hasResults && !isPipRunning && !error && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="text-center py-20"
          >
            <motion.div
              animate={{ y: [-4, 4, -4] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              className="w-16 h-16 mx-auto mb-5 rounded-2xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #7c3aed22, #00f5ff22)', border: '1px solid var(--border-glass)' }}
            >
              <Zap size={28} style={{ color: 'var(--accent)' }} />
            </motion.div>
            <p className="font-semibold mb-2">Ready to analyze</p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Enter a symbol above and click Run Analysis to start the AI pipeline.
            </p>
          </motion.div>
        )}
      </div>
    </PageWrapper>
  )
}
