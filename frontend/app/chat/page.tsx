'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import ChatWindow from '@/components/ChatWindow'
import MemoryPanel from '@/components/MemoryPanel'
import IntegrationBanner from '@/components/IntegrationBanner'
import { useWebSocket } from '@/lib/websocket'
import { getIntegrationsStatus } from '@/lib/integrations'
import { Menu, X, Settings } from 'lucide-react'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  type?: 'response' | 'file'
  filename?: string
  download_url?: string
}

interface UsageStats {
  tasks_completed: number
  tasks_failed: number
  estimated_time_saved_minutes: number
}

export default function ChatPage() {
  const router = useRouter()
  
  // Initialize empty to avoid hydration mismatch - load in useEffect
  const [messages, setMessages] = useState<Message[]>([])
  const [memories, setMemories] = useState<string[]>([])
  const [integrations, setIntegrations] = useState({ gmail: true, calendar: true })
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [showMemoryPanel, setShowMemoryPanel] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [isClient, setIsClient] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [userName, setUserName] = useState<string | null>(null)
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)

  // Client-side initialization - load localStorage data
  useEffect(() => {
    setIsClient(true)
    const storedToken = localStorage.getItem('nanobot_token')
    const storedName = localStorage.getItem('nanobot_name')
    const storedUserId = localStorage.getItem('nanobot_user_id')
    
    setToken(storedToken)
    setUserName(storedName)
    
    // Load saved messages, filtering out any with mismatched user_id in download URLs
    const saved = localStorage.getItem('nanobot_messages')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // Filter out messages with download URLs from other users
        const filtered = storedUserId 
          ? parsed.filter((m: any) => {
              if (m.download_url && !m.download_url.includes(`/files/${storedUserId}/`)) {
                return false
              }
              return true
            })
          : parsed
        setMessages(filtered.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })))
      } catch {
        // Invalid JSON, start fresh
      }
    }
  }, [])

  // Save messages to localStorage when they change
  useEffect(() => {
    if (isClient && messages.length > 0) {
      localStorage.setItem('nanobot_messages', JSON.stringify(messages))
    }
  }, [messages, isClient])

  const { sendMessage, isConnected, activeToolCall, completedTools, currentPlan } = useWebSocket({
    token: token || '',
    onMessage: (data) => {
      // Handle all message-like types: response, message, text, file
      const isMessageType = data.type === 'response' || data.type === 'message' || data.type === 'file' || data.type === 'text'
      // Also handle unknown types that have content
      const hasContent = data.content || data.message
      const isKnownNonMessage = data.type === 'typing' || data.type === 'error' || data.type === 'ping' || data.type === 'tool_start' || data.type === 'tool_done' || data.type === 'plan'
      
      if (isMessageType || (hasContent && !isKnownNonMessage)) {
        setIsTyping(false)
        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.content || data.message,
          timestamp: new Date(),
          type: data.type,
          filename: data.filename,
          download_url: data.download_url,
        }
        setMessages((prev) => [...prev, assistantMessage])

        if (data.memories) {
          setMemories(data.memories)
        }
      } else if (data.type === 'typing') {
        setIsTyping(true)
      }
    },
    onError: () => {
      setIsTyping(false)
    },
  })

  useEffect(() => {
    if (isClient && !token) {
      router.push('/')
    }
  }, [token, router, isClient])

  // Fetch integration status on mount and window focus
  const checkIntegrations = useCallback(async () => {
    if (!token) return
    try {
      const status = await getIntegrationsStatus(token)
      setIntegrations({ gmail: status.gmail, calendar: status.calendar })
    } catch {
      // Ignore errors, keep banner hidden
    }
  }, [token])

  useEffect(() => {
    checkIntegrations()

    const handleFocus = () => checkIntegrations()
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [checkIntegrations])

  // Fetch usage stats
  const fetchUsageStats = useCallback(async () => {
    if (!token) return
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765'
    try {
      const response = await fetch(`${apiUrl}/dashboard/summary?days=1&token=${token}`)
      if (response.ok) {
        const data = await response.json()
        // Only set stats if there are actual tasks
        if (data.tasks_completed > 0 || data.tasks_failed > 0) {
          setUsageStats(data)
        } else {
          setUsageStats(null)
        }
      }
    } catch (error) {
      console.error('Failed to fetch usage stats:', error)
    }
  }, [token])

  useEffect(() => {
    fetchUsageStats()
    const interval = setInterval(fetchUsageStats, 60000) // Refresh every 60 seconds
    return () => clearInterval(interval)
  }, [fetchUsageStats])

  const handleSendMessage = (content: string) => {
    // Handle /new command - clear chat locally
    if (content.trim().toLowerCase() === '/new') {
      setMessages([])
      localStorage.removeItem('nanobot_messages')
      sendMessage(content)
      return
    }
    
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setIsTyping(true)
    sendMessage(content)
  }

  // Wait for client-side hydration
  if (!isClient || !token) return null

  return (
    <div className="flex h-screen bg-nano-bg">
      {/* Top buttons */}
      <div className="fixed top-4 right-4 z-50 flex items-center gap-2">
        <button
          onClick={() => router.push('/integrations')}
          className="p-2 bg-nano-card border border-nano-border rounded-lg hover:bg-nano-border transition-colors"
          title="Integrations"
        >
          <Settings className="w-5 h-5 text-nano-muted" />
        </button>
        <button
          onClick={() => setShowMemoryPanel(!showMemoryPanel)}
          className="lg:hidden p-2 bg-nano-card border border-nano-border rounded-lg"
        >
          {showMemoryPanel ? (
            <X className="w-5 h-5 text-nano-muted" />
          ) : (
            <Menu className="w-5 h-5 text-nano-muted" />
          )}
        </button>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Integration banner */}
        {!bannerDismissed && (
          <IntegrationBanner
            gmail={integrations.gmail}
            calendar={integrations.calendar}
            onDismiss={() => setBannerDismissed(true)}
          />
        )}

        {/* Usage stats bar */}
        {usageStats && (
          <div className="text-xs text-gray-400 text-center py-2 border-b border-gray-800">
            📊 Today: {usageStats.tasks_completed + usageStats.tasks_failed} tasks ·
            ⏱️ ~{usageStats.estimated_time_saved_minutes} min saved ·
            ✅ {usageStats.tasks_completed} ·
            ❌ {usageStats.tasks_failed}
          </div>
        )}

        {/* Chat window */}
        <ChatWindow
          messages={messages}
          isTyping={isTyping}
          isConnected={isConnected}
          userName={userName || 'User'}
          onSendMessage={handleSendMessage}
          activeToolCall={activeToolCall}
          completedTools={completedTools}
          currentPlan={currentPlan}
        />
      </div>

      {/* Memory panel */}
      <div
        className={`fixed lg:relative inset-y-0 right-0 w-80 transform transition-transform duration-300 ease-in-out z-40
                    ${showMemoryPanel ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'}`}
      >
        <MemoryPanel memories={memories} />
      </div>
    </div>
  )
}
