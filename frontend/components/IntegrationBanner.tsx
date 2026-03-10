'use client'

import { X, Mail, Calendar } from 'lucide-react'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

interface IntegrationBannerProps {
  gmail: boolean
  calendar: boolean
  onDismiss: () => void
}

export default function IntegrationBanner({ gmail, calendar, onDismiss }: IntegrationBannerProps) {
  const router = useRouter()
  
  // Don't show if both are connected
  if (gmail && calendar) {
    return null
  }
  
  const missing: string[] = []
  if (!gmail) missing.push('Gmail')
  if (!calendar) missing.push('Calendar')
  
  return (
    <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 border-b border-nano-border px-4 py-3">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            {!gmail && <Mail className="w-4 h-4 text-blue-400" />}
            {!calendar && <Calendar className="w-4 h-4 text-purple-400" />}
          </div>
          <span className="text-sm text-nano-text">
            Connect {missing.join(' & ')} to unlock full features
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push('/integrations')}
            className="px-3 py-1.5 text-sm font-medium bg-nano-accent hover:bg-nano-accent/80 text-white rounded-lg transition-colors"
          >
            Connect
          </button>
          <button
            onClick={onDismiss}
            className="p-1 text-nano-muted hover:text-nano-text transition-colors"
            title="Dismiss for this session"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
