/**
 * Navbar.jsx — Fixed top navigation.
 * Scroll progress bar + animated shrink + spring active-route pill.
 * z-index: 50 (below scanlines overlay at 9998).
 */
import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { motion, useScroll, useSpring } from 'framer-motion'
import { Activity, BarChart2, History, Zap } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/',        label: 'Dashboard', icon: Activity  },
  { to: '/analyze', label: 'Analyze',   icon: BarChart2 },
  { to: '/history', label: 'History',   icon: History   },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  /* Scroll progress for top indicator */
  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, { stiffness: 200, damping: 30 })

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      {/* ── Scroll Progress ── */}
      <motion.div
        style={{
          scaleX,
          position: 'fixed', top: 0, left: 0, right: 0,
          height: '2px', originX: 0, zIndex: 60,
          background: 'linear-gradient(90deg, var(--gradient-a), var(--accent))',
        }}
      />

      {/* ── Navbar Shell ── */}
      <motion.header
        animate={{
          height:          scrolled ? 52 : 64,
          backdropFilter:  scrolled ? 'blur(28px)' : 'blur(14px)',
          backgroundColor: scrolled ? 'rgba(10,10,15,0.94)' : 'rgba(10,10,15,0.55)',
        }}
        transition={{ duration: 0.28, ease: 'easeOut' }}
        style={{
          position:    'fixed',
          top:         '2px',   /* sits just below progress bar */
          left:         0,
          right:        0,
          zIndex:       50,
          borderBottom: '1px solid var(--border-glass)',
        }}
      >
        <div
          className="page-container h-full flex items-center justify-between gap-6"
          style={{ height: '100%' }}
        >
          {/* Brand */}
          <NavLink to="/" className="flex items-center gap-2.5 shrink-0 select-none">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
              className="flex items-center justify-center rounded-full shrink-0"
              style={{
                width: 30, height: 30,
                background: 'linear-gradient(135deg, var(--gradient-a), var(--accent))',
              }}
            >
              <Zap size={14} color="#fff" />
            </motion.div>
            <motion.span
              animate={{ fontSize: scrolled ? '10px' : '11px' }}
              transition={{ duration: 0.28 }}
              className="font-bold tracking-[0.18em] uppercase gradient-accent-text hidden sm:block"
            >
              Agentic Quant
            </motion.span>
          </NavLink>

          {/* Nav links */}
          <nav className="flex items-center gap-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === '/'}>
                {({ isActive }) => (
                  <motion.div
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.95 }}
                    className="relative flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-medium select-none"
                    style={{ color: isActive ? 'var(--accent)' : 'var(--text-muted)' }}
                  >
                    {isActive && (
                      <motion.span
                        layoutId="nav-active-pill"
                        className="absolute inset-0 rounded-lg"
                        style={{ background: 'var(--accent-dim)', border: '1px solid rgba(0,245,255,0.2)' }}
                        transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                      />
                    )}
                    <Icon size={13} className="relative z-10 shrink-0" />
                    <span className="relative z-10">{label}</span>
                  </motion.div>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Live badge */}
          <div
            className="flex items-center gap-2 text-[11px] font-mono tracking-widest shrink-0"
            style={{ color: 'var(--text-muted)' }}
          >
            <motion.span
              animate={{ opacity: [1, 0.2, 1] }}
              transition={{ duration: 1.8, repeat: Infinity }}
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ background: 'var(--accent)' }}
            />
            <span className="hidden sm:block">LIVE</span>
          </div>
        </div>
      </motion.header>
    </>
  )
}
