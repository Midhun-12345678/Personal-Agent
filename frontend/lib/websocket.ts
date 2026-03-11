'use client'

import { useEffect, useRef, useCallback, useState } from 'react'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8765'

export interface ToolEvent {
  type: 'tool_start' | 'tool_done'
  tool: string
  description: string
}

export interface PlanEvent {
  type: 'plan'
  steps: string[]
  tools: string[]
  formatted?: string
}

interface UseWebSocketOptions {
  token: string
  onMessage: (data: any) => void
  onError?: (error: Event) => void
}

export function useWebSocket({ token, onMessage, onError }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const [isConnected, setIsConnected] = useState(false)
  const [activeToolCall, setActiveToolCall] = useState<ToolEvent | null>(null)
  const [completedTools, setCompletedTools] = useState<ToolEvent[]>([])
  const [currentPlan, setCurrentPlan] = useState<PlanEvent | null>(null)
  const onMessageRef = useRef(onMessage)
  const onErrorRef = useRef(onError)

  // Keep refs updated without triggering reconnects
  useEffect(() => {
    onMessageRef.current = onMessage
    onErrorRef.current = onError
  }, [onMessage, onError])

  const connect = useCallback(() => {
    if (!token) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return

    const ws = new WebSocket(`${WS_URL}/ws/${token}`)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'ping') return  // ignore keepalive pings

        // Handle tool-related events
        if (data.type === 'tool_start') {
          console.log('Tool started:', data)
          const toolEvent: ToolEvent = {
            type: 'tool_start',
            tool: data.tool,
            description: data.description
          }
          setActiveToolCall(toolEvent)
          setCompletedTools(prev => [...prev, toolEvent])
        } else if (data.type === 'tool_done') {
          console.log('Tool completed:', data)
          const toolEvent: ToolEvent = {
            type: 'tool_done',
            tool: data.tool,
            description: data.description
          }
          // Update the matching tool_start entry to tool_done
          setCompletedTools(prev =>
            prev.map((t, idx) =>
              idx === prev.length - 1 && t.type === 'tool_start' && t.tool === data.tool
                ? toolEvent
                : t
            )
          )
          setActiveToolCall(null)
        } else if (data.type === 'plan') {
          console.log('Plan received:', data)
          // Try to parse content if it's a JSON string
          let planData = data
          if (typeof data.content === 'string') {
            try {
              planData = JSON.parse(data.content)
            } catch {
              // Content is not JSON, use data as-is
            }
          }
          const planEvent: PlanEvent = {
            type: 'plan',
            steps: planData.steps || [],
            tools: planData.tools || [],
            formatted: planData.formatted
          }
          setCurrentPlan(planEvent)
        } else if (data.type === 'response' || data.type === 'message' || data.type === 'text') {
          console.log('Message received, clearing tool state')
          // New turn starting - clear all tool state
          setActiveToolCall(null)
          setCompletedTools([])
          setCurrentPlan(null)
        } else if (data.type !== 'typing' && data.type !== 'error') {
          // Unknown type but has content - treat as message
          if (data.content || data.message) {
            console.log('Unknown message type with content:', data.type)
            setActiveToolCall(null)
            setCompletedTools([])
            setCurrentPlan(null)
          }
        }

        // Pass to original handler
        onMessageRef.current(data)
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      onErrorRef.current?.(error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
      wsRef.current = null

      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect()
      }, 3000)
    }
  }, [token])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', content }))
    }
  }, [])

  return {
    sendMessage,
    isConnected,
    activeToolCall,
    completedTools,
    currentPlan
  }
}
