'use client'

import { Brain, Sparkles } from 'lucide-react'

interface MemoryPanelProps {
  memories: string[]
}

export default function MemoryPanel({ memories }: MemoryPanelProps) {
  return (
    <div className="h-full bg-nano-card border-l border-nano-border p-6 overflow-y-auto">
      <div className="flex items-center gap-2 mb-6">
        <Brain className="w-5 h-5 text-nano-accent" />
        <h2 className="font-semibold text-nano-text">Memory</h2>
      </div>

      {memories.length === 0 ? (
        <div className="text-center py-8">
          <Sparkles className="w-8 h-8 text-nano-muted mx-auto mb-3" />
          <p className="text-sm text-nano-muted">
            As we chat, I'll remember important things about you here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {memories.map((memory, index) => (
            <div
              key={index}
              className="p-3 bg-nano-bg border border-nano-border rounded-xl"
            >
              <p className="text-sm text-nano-text">{memory}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
