'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { ToolEvent, PlanEvent } from '@/lib/websocket'

interface ToolCallIndicatorProps {
  activeToolCall: ToolEvent | null
  completedTools: ToolEvent[]
  currentPlan: PlanEvent | null
}

const TOOL_EMOJIS: Record<string, string> = {
  gmail: '📧',
  calendar: '📅',
  write_file: '📁',
  read_file: '📁',
  edit_file: '📁',
  web_search: '🔍',
  web_fetch: '🔍',
  exec: '⚙️',
  memory: '🧠',
  browser: '🌐',
}

const getToolEmoji = (tool: string): string => {
  return TOOL_EMOJIS[tool] || '🔧'
}

export default function ToolCallIndicator({
  activeToolCall,
  completedTools,
  currentPlan,
}: ToolCallIndicatorProps) {
  const [planCollapsed, setPlanCollapsed] = useState(false)

  // Collapse plan when any tool starts executing
  const shouldCollapsePlan = completedTools.length > 0

  // Don't render if nothing to show
  if (!activeToolCall && completedTools.length === 0 && !currentPlan) {
    return null
  }

  return (
    <div className="px-6 py-3 space-y-2 transition-opacity duration-200">
      {/* Plan Card */}
      {currentPlan && (
        <div className="border border-gray-700 rounded-lg bg-gray-900 overflow-hidden">
          <button
            onClick={() => setPlanCollapsed(!planCollapsed)}
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800 transition-colors"
          >
            <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
              <span>📋</span>
              <span>Task Plan</span>
            </div>
            {shouldCollapsePlan && !planCollapsed ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            )}
          </button>

          {(!planCollapsed || !shouldCollapsePlan) && (
            <div className="px-4 pb-3 space-y-1">
              {currentPlan.steps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-2 text-xs text-gray-400">
                  <span className="text-gray-600">{idx + 1}</span>
                  <span>→</span>
                  <span>{step}</span>
                  <span>{getToolEmoji(currentPlan.tools[idx] || '')}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Active and Completed Tools */}
      {completedTools.length > 0 && (
        <div className="space-y-1">
          {completedTools.slice(-5).map((tool, idx) => (
            <div
              key={idx}
              className={`flex items-center gap-2 text-xs ${
                tool.type === 'tool_done'
                  ? 'text-gray-500'
                  : 'text-blue-400'
              }`}
            >
              {tool.type === 'tool_done' ? (
                <span>✓</span>
              ) : (
                <div className="animate-spin h-3 w-3 border border-blue-400 border-t-transparent rounded-full" />
              )}
              <span>{tool.description}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
