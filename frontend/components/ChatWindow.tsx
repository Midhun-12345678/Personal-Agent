'use client'

import { useEffect, useRef } from 'react'
import { Message } from '@/app/chat/page'
import MessageBubble from './MessageBubble'
import InputBar from './InputBar'
import ToolCallIndicator from './ToolCallIndicator'
import { Bot, Wifi, WifiOff } from 'lucide-react'
import { ToolEvent, PlanEvent } from '@/lib/websocket'

interface ChatWindowProps {
  messages: Message[]
  isTyping: boolean
  isConnected: boolean
  userName: string
  onSendMessage: (content: string) => void
  activeToolCall?: ToolEvent | null
  completedTools?: ToolEvent[]
  currentPlan?: PlanEvent | null
}

export default function ChatWindow({
  messages,
  isTyping,
  isConnected,
  userName,
  onSendMessage,
  activeToolCall = null,
  completedTools = [],
  currentPlan = null,
}: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-nano-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-nano-accent/20 flex items-center justify-center">
            <Bot className="w-5 h-5 text-nano-accent" />
          </div>
          <div>
            <h1 className="font-semibold text-nano-text">YourBot</h1>
            <p className="text-xs text-nano-muted">
              {isConnected ? 'Online' : 'Reconnecting...'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <Wifi className="w-4 h-4 text-green-500" />
          ) : (
            <WifiOff className="w-4 h-4 text-red-500" />
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-nano-accent/20 flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-nano-accent" />
            </div>
            <h2 className="text-xl font-semibold text-nano-text mb-2">
              Hi {userName}!
            </h2>
            <p className="text-nano-muted max-w-md">
              I'm your personal AI assistant. Ask me anything or tell me about yourself so I can help you better.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isTyping && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-nano-accent/20 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-nano-accent" />
            </div>
            <div className="bg-nano-card border border-nano-border rounded-2xl rounded-tl-none px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-nano-muted rounded-full typing-dot" />
                <span className="w-2 h-2 bg-nano-muted rounded-full typing-dot" />
                <span className="w-2 h-2 bg-nano-muted rounded-full typing-dot" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Tool Call Indicator */}
      <ToolCallIndicator
        activeToolCall={activeToolCall}
        completedTools={completedTools}
        currentPlan={currentPlan}
      />

      {/* Input */}
      <InputBar onSend={onSendMessage} disabled={!isConnected} />
    </div>
  )
}
