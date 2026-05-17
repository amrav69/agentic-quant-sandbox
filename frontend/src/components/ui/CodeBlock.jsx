/**
 * CodeBlock.jsx
 * Syntax-styled code display panel.
 *
 * Props:
 *  - code (string)      : The code content to display
 *  - language (string)  : Language label shown in header (default: "python")
 *  - title (string?)    : Optional panel title
 *  - maxHeight (string) : Max scrollable height (default: "400px")
 */
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Copy, Check, Terminal } from 'lucide-react'
import { fadeUp } from '../animations/motionVariants'

/* ── Very lightweight token coloriser (no heavy deps) ── */
function colorisePython(code) {
  if (!code) return []

  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  const lines = code.split('\n')
  return lines.map((line, i) => {
    const escaped = esc(line)

    // 1. Detect if line starts a comment (trim to find leading #)
    const trimmed = line.trimStart()
    if (trimmed.startsWith('#')) {
      return {
        lineNumber: i + 1,
        colored: `<span style="color:#475569;font-style:italic">${escaped}</span>`,
      }
    }

    // 2. Check for inline comment – split at first # not inside string
    let codePart = escaped
    let commentPart = ''
    const commentIdx = escaped.search(/#/)
    if (commentIdx !== -1) {
      codePart    = escaped.slice(0, commentIdx)
      commentPart = `<span style="color:#475569;font-style:italic">${escaped.slice(commentIdx)}</span>`
    }

    // 3. Apply token colorization only on the non-comment portion
    const colored = codePart
      // Strings
      .replace(/("""[\s\S]*?"""|'''[\s\S]*?'''|"[^"]*"|'[^']*')/g,
        '<span style="color:#a3e635">$1</span>')
      // Keywords
      .replace(/\b(import|from|as|def|class|return|if|elif|else|for|while|in|not|and|or|is|None|True|False|try|except|raise|with|pass|break|continue|async|await|lambda|yield)\b/g,
        '<span style="color:#c084fc">$1</span>')
      // Built-ins
      .replace(/\b(print|len|range|str|int|float|list|dict|tuple|set|bool|type)\b/g,
        '<span style="color:#38bdf8">$1</span>')
      // Numbers
      .replace(/\b(\d[\d_.]*)\b/g,
        '<span style="color:#fb923c">$1</span>')
      // Decorators
      .replace(/(@\w+)/g,
        '<span style="color:#f472b6">$1</span>')

    return { lineNumber: i + 1, colored: colored + commentPart }
  })
}

export default function CodeBlock({
  code = '',
  language = 'python',
  title,
  maxHeight = '420px',
}) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const lines = colorisePython(code)

  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="visible"
      className="glass rounded-2xl overflow-hidden"
      style={{ border: '1px solid var(--border-glass)' }}
    >
      {/* ── Header bar ── */}
      <div className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: 'var(--border-glass)', background: 'rgba(255,255,255,0.02)' }}>

        <div className="flex items-center gap-3">
          {/* Traffic lights */}
          <div className="flex gap-1.5">
            {['#ef4444','#f59e0b','#10b981'].map((c) => (
              <div key={c} className="w-2.5 h-2.5 rounded-full" style={{ background: c }} />
            ))}
          </div>
          <Terminal size={13} style={{ color: 'var(--text-muted)' }} />
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {title ?? language}
          </span>
        </div>

        {/* Copy button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-[11px] font-mono px-3 py-1.5 rounded-lg transition-colors"
          style={{
            color:      copied ? '#10b981' : 'var(--text-muted)',
            background: copied ? '#10b98118' : 'rgba(255,255,255,0.04)',
            border:     `1px solid ${copied ? '#10b98130' : 'var(--border-glass)'}`,
          }}
        >
          <AnimatePresence mode="wait" initial={false}>
            {copied ? (
              <motion.span key="check"
                initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.6, opacity: 0 }} transition={{ duration: 0.15 }}>
                <Check size={12} />
              </motion.span>
            ) : (
              <motion.span key="copy"
                initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.6, opacity: 0 }} transition={{ duration: 0.15 }}>
                <Copy size={12} />
              </motion.span>
            )}
          </AnimatePresence>
          {copied ? 'Copied!' : 'Copy'}
        </motion.button>
      </div>

      {/* ── Code body ── */}
      <div className="overflow-auto" style={{ maxHeight }}>
        <table className="w-full border-collapse text-sm font-mono">
          <tbody>
            {lines.map(({ colored, lineNumber }) => (
              <tr key={lineNumber}
                className="hover:bg-white/[0.02] transition-colors">
                {/* Line numbers */}
                <td className="select-none text-right pr-4 pl-4 py-0.5 w-10 shrink-0 text-[11px]"
                  style={{ color: 'var(--text-muted)', userSelect: 'none', opacity: 0.5 }}>
                  {lineNumber}
                </td>
                {/* Code */}
                <td className="pr-6 py-0.5 whitespace-pre"
                  style={{ color: '#e2e8f0' }}
                  dangerouslySetInnerHTML={{ __html: colored }} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  )
}
