/**
 * CriticPanel.jsx
 * Step 3 agent card — PASS/FAIL verdict, shake on FAIL, issues + suggestions list.
 */
import { motion } from 'framer-motion'
import { Shield, CheckCircle, XCircle, AlertTriangle, Lightbulb } from 'lucide-react'
import { staggerContainer, fadeUp } from '../animations/motionVariants'

export default function CriticPanel({ verdict = 'FAIL', issues = [], suggestions = [] }) {
  const isPass   = verdict === 'PASS'
  const color    = isPass ? '#10b981' : '#ef4444'
  const VIcon    = isPass ? CheckCircle : XCircle

  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="visible"
      className="rounded-2xl overflow-hidden"
      style={{ border: `2px solid ${color}50`, background: `${color}05`, boxShadow: `0 0 40px ${color}12` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: `${color}20` }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${color}18` }}>
            <Shield size={16} style={{ color }} />
          </div>
          <div>
            <p className="font-semibold text-sm">Critic Agent</p>
            <p className="text-[10px] uppercase tracking-widest" style={{ color }}>Step 3 · Risk Review</p>
          </div>
        </div>

        {/* Verdict badge — shakes on FAIL */}
        <motion.div
          animate={!isPass ? { x: [-10, 10, -8, 8, -4, 4, 0] } : {}}
          transition={{ duration: 0.55, delay: 0.4 }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl font-mono font-bold text-sm"
          style={{ color, background: `${color}18`, border: `1px solid ${color}40` }}
        >
          <VIcon size={16} />
          {verdict}
        </motion.div>
      </div>

      <div className="px-6 py-5 space-y-6">
        {/* Issues */}
        {issues.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle size={14} style={{ color: '#f59e0b' }} />
              <p className="text-xs uppercase tracking-widest font-semibold" style={{ color: '#f59e0b' }}>
                Issues Found ({issues.length})
              </p>
            </div>
            <motion.ul
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
              className="space-y-2"
            >
              {issues.map((issue, i) => (
                <motion.li key={i} variants={fadeUp}
                  className="flex gap-3 text-sm py-2.5 px-3 rounded-lg"
                  style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}>
                  <span className="shrink-0 font-mono text-xs mt-0.5" style={{ color: '#ef4444' }}>{i + 1}.</span>
                  <span style={{ color: 'var(--text-muted)' }}>{issue}</span>
                </motion.li>
              ))}
            </motion.ul>
          </div>
        )}

        {/* Suggestions */}
        {suggestions.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb size={14} style={{ color: '#10b981' }} />
              <p className="text-xs uppercase tracking-widest font-semibold" style={{ color: '#10b981' }}>
                Suggestions ({suggestions.length})
              </p>
            </div>
            <motion.ul
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
              className="space-y-2"
            >
              {suggestions.map((s, i) => (
                <motion.li key={i} variants={fadeUp}
                  className="flex gap-3 text-sm py-2.5 px-3 rounded-lg"
                  style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.15)' }}>
                  <span className="shrink-0 font-mono text-xs mt-0.5" style={{ color: '#10b981' }}>→</span>
                  <span style={{ color: 'var(--text-muted)' }}>{s}</span>
                </motion.li>
              ))}
            </motion.ul>
          </div>
        )}
      </div>
    </motion.div>
  )
}
