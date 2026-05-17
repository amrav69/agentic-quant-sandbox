/**
 * Navbar.jsx
 * Enhanced sticky navbar with:
 * - scroll-progress indicator
 * - animated shrink on scroll
 * - glassmorphism with dynamic blur intensity
 * - active route highlighting
 * - animated rotating brand logo
 */
import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { motion, useScroll, useSpring, AnimatePresence } from 'framer-motion'
import { Activity, BarChart2, History, Zap } from 'lucide-react'

const navItems = [
  { to: '/',        label: 'Dashboard', icon: Activity  },
  { to: '/analyze', label: 'Analyze',   icon: BarChart2 },
  { to: '/history', label: 'History',   icon: History   },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  // Scroll progress for the top bar indicator
  const { scrollYProgress } = useScroll()
  const scaleX = useSpring(scrollYProgress, { stiffness: 200, damping: 30 })

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      {/* ── Scroll Progress Bar ── */}
      <motion.div
        className="fixed top-0 left-0 right-0 z-[60] h-[2px] origin-left"
        style={{
          scaleX,
          background: 'linear-gradient(90deg, #7c3aed, #00f5ff)',
        }}
      />

      {/* ── Navbar ── */}
      <motion.header
        animate={{
          height:            scrolled ? 52 : 64,
          backdropFilter:    scrolled ? 'blur(24px)' : 'blur(12px)',
          backgroundColor:   scrolled ? 'rgba(10,10,15,0.92)' : 'rgba(10,10,15,0.6)',
        }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="fixed top-[2px] left-0 right-0 z-50 border-b"
        style={{ borderColor: 'var(--border-glass)' }}
      >
        <div className="max-w-screen-xl mx-auto px-6 h-full flex items-center justify-between">

          {/* Brand */}
          <NavLink to="/" className="flex items-center gap-3 shrink-0">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
              className="w-8 h-8 rounded-full flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #00f5ff)' }}
            >
              <Zap size={15} className="text-white" />
            </motion.div>
            <motion.span
              animate={{ fontSize: scrolled ? '11px' : '12px' }}
              transition={{ duration: 0.3 }}
              className="font-bold tracking-widest uppercase gradient-accent-text"
            >
              Agentic Quant
            </motion.span>
          </NavLink>

          {/* Nav Links */}
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === '/'}>
                {({ isActive }) => (
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.96 }}
                    className="relative flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-colors"
                    style={{ color: isActive ? 'var(--accent)' : 'var(--text-muted)' }}
                  >
                    {isActive && (
                      <motion.span
                        layoutId="nav-pill"
                        className="absolute inset-0 rounded-lg"
                        style={{ background: 'var(--accent-dim)' }}
                        transition={{ type: 'spring', stiffness: 400, damping: 35 }}
                      />
                    )}
                    <Icon size={14} className="relative z-10" />
                    <span className="relative z-10">{label}</span>
                  </motion.div>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Live badge */}
          <div className="flex items-center gap-2 text-xs font-mono shrink-0"
            style={{ color: 'var(--text-muted)' }}>
            <motion.span
              animate={{ opacity: [1, 0.2, 1] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: 'var(--accent)' }}
            />
            LIVE
          </div>
        </div>
      </motion.header>
    </>
  )
}
