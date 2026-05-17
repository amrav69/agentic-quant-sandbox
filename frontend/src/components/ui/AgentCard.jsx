/**
 * AgentCard.jsx
 * Premium status card for AI agents.
 *
 * Props:
 *  - label (string)         : Agent name e.g. "Research Agent"
 *  - icon (LucideIcon)      : Icon component
 *  - status (string)        : "ONLINE" | "OFFLINE" | "RUNNING" | "LIVE"
 *  - accentColor (string)   : CSS color string e.g. "#00f5ff"
 *  - description (string?)  : Optional subtitle text
 *  - onClick (fn?)          : Optional click handler
 */
import { motion } from 'framer-motion'
import { cardHover, fadeUp } from '../animations/motionVariants'

const STATUS_COLORS = {
  ONLINE:  '#10b981',
  LIVE:    '#00f5ff',
  RUNNING: '#f59e0b',
  OFFLINE: '#ef4444',
  IDLE:    '#64748b',
}

export default function AgentCard({
  label,
  icon: Icon,
  status = 'ONLINE',
  accentColor = '#00f5ff',
  description,
  onClick,
}) {
  const statusColor = STATUS_COLORS[status] ?? STATUS_COLORS.ONLINE
  const isRunning = status === 'RUNNING'

  return (
    <motion.div
      variants={fadeUp}
      initial="rest"
      whileHover="hover"
      animate="rest"
      onClick={onClick}
      className="relative glass rounded-2xl p-5 overflow-hidden cursor-pointer select-none"
      style={{
        borderLeft: `2px solid ${accentColor}`,
        border:     `1px solid var(--border-glass)`,
        borderLeftWidth: '3px',
        borderLeftColor: accentColor,
      }}
    >
      {/* Hover glow layer */}
      <motion.div
        variants={{
          rest:  { opacity: 0 },
          hover: { opacity: 1 },
        }}
        transition={{ duration: 0.3 }}
        className="absolute inset-0 rounded-2xl pointer-events-none"
        style={{
          background: `radial-gradient(ellipse at 0% 50%, ${accentColor}10 0%, transparent 70%)`,
        }}
      />

      {/* Card Content */}
      <div className="relative z-10">
        {/* Header row */}
        <div className="flex items-start justify-between mb-4">
          <motion.div
            whileHover={{ scale: 1.1, rotate: 5 }}
            transition={{ type: 'spring', stiffness: 400 }}
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: `${accentColor}18` }}
          >
            <Icon size={19} style={{ color: accentColor }} />
          </motion.div>

          {/* Status pill */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full"
            style={{ background: `${statusColor}18` }}>
            {/* Pulse dot */}
            <motion.span
              animate={isRunning
                ? { scale: [1, 1.4, 1], opacity: [1, 0.5, 1] }
                : { opacity: [1, 0.4, 1] }
              }
              transition={{ duration: isRunning ? 0.8 : 2, repeat: Infinity }}
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: statusColor }}
            />
            <span className="text-[10px] font-mono font-semibold tracking-widest"
              style={{ color: statusColor }}>
              {status}
            </span>
          </div>
        </div>

        {/* Label */}
        <p className="font-semibold text-sm mb-1" style={{ color: 'var(--text-primary)' }}>
          {label}
        </p>

        {/* Description */}
        {description && (
          <motion.p
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xs leading-relaxed"
            style={{ color: 'var(--text-muted)' }}
          >
            {description}
          </motion.p>
        )}
      </div>
    </motion.div>
  )
}
