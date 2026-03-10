'use client'

import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'

interface InputBarProps {
  onSend: (content: string) => void
  disabled?: boolean
}

export default function InputBar({ onSend, disabled }: InputBarProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`
    }
  }, [input])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || disabled) return

    onSend(input.trim())
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-nano-border px-6 py-4"
    >
      <div className="flex items-end gap-3 bg-nano-card border border-nano-border rounded-2xl px-4 py-3">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent text-nano-text placeholder-nano-muted 
                     resize-none focus:outline-none text-sm max-h-[120px]"
        />
        <button
          type="submit"
          disabled={!input.trim() || disabled}
          className="p-2 bg-nano-accent hover:bg-nano-accent-hover disabled:opacity-50 
                     disabled:cursor-not-allowed rounded-xl transition-colors"
        >
          <Send className="w-4 h-4 text-white" />
        </button>
      </div>
      <p className="text-xs text-nano-muted text-center mt-2">
        Press Enter to send, Shift + Enter for new line
      </p>
    </form>
  )
}
