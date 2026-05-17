/**
 * useTypingEffect.js
 * Custom hook that simulates a typewriter character-by-character reveal.
 *
 * @param {string}  text        - The full string to type out
 * @param {number}  speed       - Milliseconds between each character (default: 55)
 * @param {number}  startDelay  - Milliseconds before typing begins (default: 400)
 * @returns {{ displayed: string, isDone: boolean }}
 */
import { useState, useEffect } from 'react'

export default function useTypingEffect(text, speed = 55, startDelay = 400) {
  const [displayed, setDisplayed] = useState('')
  const [isDone, setIsDone]       = useState(false)

  useEffect(() => {
    setDisplayed('')
    setIsDone(false)

    let index   = 0
    let timeout = null

    const startTyping = () => {
      const tick = () => {
        index++
        setDisplayed(text.slice(0, index))
        if (index < text.length) {
          timeout = setTimeout(tick, speed)
        } else {
          setIsDone(true)
        }
      }
      timeout = setTimeout(tick, speed)
    }

    const delayTimer = setTimeout(startTyping, startDelay)

    return () => {
      clearTimeout(delayTimer)
      clearTimeout(timeout)
    }
  }, [text, speed, startDelay])

  return { displayed, isDone }
}
