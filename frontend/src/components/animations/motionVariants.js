/**
 * motionVariants.js
 * Centralized Framer Motion animation presets for the Agentic Quant Sandbox.
 * Import specific variants wherever needed across the app.
 */

/* ─── fadeUp ─────────────────────────────────────────────────────────────────
   Use for: content cards, sections appearing on load or scroll.
   Effect: element slides up from slightly below and fades in.
─────────────────────────────────────────────────────────────────────────────*/
export const fadeUp = {
  hidden: {
    opacity: 0,
    y: 24,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1], // expo out - snappy but elegant
    },
  },
  exit: {
    opacity: 0,
    y: -12,
    transition: { duration: 0.25, ease: 'easeIn' },
  },
}

/* ─── staggerContainer ───────────────────────────────────────────────────────
   Use for: wrapping lists or grids of cards to stagger their animations.
   Children need their own variant (e.g. fadeUp) to be triggered by this.
─────────────────────────────────────────────────────────────────────────────*/
export const staggerContainer = {
  hidden:  { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren:  0.08,
      delayChildren:    0.1,
    },
  },
  exit: {
    opacity: 0,
    transition: { staggerChildren: 0.05, staggerDirection: -1 },
  },
}

/* ─── pageTransition ─────────────────────────────────────────────────────────
   Use for: wrapping entire page components to animate route changes.
   Effect: cinematic fade + subtle vertical drift.
─────────────────────────────────────────────────────────────────────────────*/
export const pageTransition = {
  hidden: {
    opacity: 0,
    y: 16,
    filter: 'blur(4px)',
  },
  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: 0.45,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -8,
    filter: 'blur(2px)',
    transition: { duration: 0.25, ease: 'easeIn' },
  },
}

/* ─── cardHover ──────────────────────────────────────────────────────────────
   Use for: interactive glass cards and panels.
   Note: apply via whileHover on the motion element, not as animate variants.
─────────────────────────────────────────────────────────────────────────────*/
export const cardHover = {
  rest: {
    scale: 1,
    boxShadow: '0 0 0px rgba(0, 245, 255, 0)',
    borderColor: 'rgba(255, 255, 255, 0.08)',
    transition: { duration: 0.3, ease: 'easeOut' },
  },
  hover: {
    scale: 1.015,
    boxShadow: '0 0 30px rgba(0, 245, 255, 0.12), 0 0 80px rgba(0, 245, 255, 0.04)',
    borderColor: 'rgba(0, 245, 255, 0.25)',
    transition: { duration: 0.3, ease: 'easeOut' },
  },
}

/* ─── modalReveal ────────────────────────────────────────────────────────────
   Use for: modals, drawers, overlays, and toast panels.
   Effect: scales up from 95% with blur fade-in.
─────────────────────────────────────────────────────────────────────────────*/
export const modalReveal = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: 12,
    filter: 'blur(8px)',
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: {
      duration: 0.4,
      ease: [0.16, 1, 0.3, 1],
    },
  },
  exit: {
    opacity: 0,
    scale: 0.96,
    y: 8,
    filter: 'blur(4px)',
    transition: { duration: 0.22, ease: 'easeIn' },
  },
}

/* ─── slideInLeft ────────────────────────────────────────────────────────────
   Use for: sidebars, notification panels entering from the left.
─────────────────────────────────────────────────────────────────────────────*/
export const slideInLeft = {
  hidden:  { opacity: 0, x: -32 },
  visible: {
    opacity: 1, x: 0,
    transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] },
  },
  exit: {
    opacity: 0, x: -16,
    transition: { duration: 0.22, ease: 'easeIn' },
  },
}

/* ─── pulseGlow ──────────────────────────────────────────────────────────────
   Use for: status indicators, live data badges.
   Note: use animate prop (not variants) for looping.
─────────────────────────────────────────────────────────────────────────────*/
export const pulseGlowAnim = {
  animate: {
    boxShadow: [
      '0 0 4px rgba(0, 245, 255, 0.4)',
      '0 0 16px rgba(0, 245, 255, 0.8)',
      '0 0 4px rgba(0, 245, 255, 0.4)',
    ],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
}
