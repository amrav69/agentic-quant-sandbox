/**
 * LoadingSkeleton.jsx
 * Animated shimmer skeleton placeholders.
 *
 * Components exported:
 *  - SkeletonBlock  : Single shimmer rectangle (configurable width/height/radius)
 *  - SkeletonCard   : Full glass card with stacked skeleton lines
 *  - SkeletonAgentCard : Mimics AgentCard layout
 */
import { motion } from 'framer-motion'

/* ── Shimmer animation variant ── */
const shimmer = {
  initial: { backgroundPosition: '200% 0' },
  animate: {
    backgroundPosition: ['-200% 0', '200% 0'],
    transition: { duration: 1.8, repeat: Infinity, ease: 'linear' },
  },
}

/* ── SkeletonBlock ── */
export function SkeletonBlock({ width = '100%', height = '16px', rounded = '8px', className = '' }) {
  return (
    <motion.div
      variants={shimmer}
      initial="initial"
      animate="animate"
      className={className}
      style={{
        width,
        height,
        borderRadius: rounded,
        background: 'linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.04) 75%)',
        backgroundSize: '400% 100%',
      }}
    />
  )
}

/* ── SkeletonCard ── */
export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="glass rounded-2xl p-5 space-y-3">
      {/* Icon + badge row */}
      <div className="flex items-center justify-between">
        <SkeletonBlock width="40px" height="40px" rounded="12px" />
        <SkeletonBlock width="64px" height="24px" rounded="99px" />
      </div>
      {/* Text lines */}
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonBlock
          key={i}
          width={i === 0 ? '60%' : i === lines - 1 ? '40%' : '85%'}
          height="12px"
          rounded="6px"
        />
      ))}
    </div>
  )
}

/* ── SkeletonAgentCard : same layout as AgentCard ── */
export function SkeletonAgentCard() {
  return (
    <div className="glass rounded-2xl p-5 border-l-[3px]"
      style={{ borderLeftColor: 'rgba(255,255,255,0.08)' }}>
      <div className="flex items-start justify-between mb-4">
        <SkeletonBlock width="40px" height="40px" rounded="12px" />
        <SkeletonBlock width="72px" height="22px" rounded="99px" />
      </div>
      <SkeletonBlock width="55%" height="13px" rounded="6px" className="mb-2" />
      <SkeletonBlock width="80%" height="10px" rounded="6px" />
    </div>
  )
}

/* ── Default export: generic skeleton for arbitrary use ── */
export default SkeletonBlock
