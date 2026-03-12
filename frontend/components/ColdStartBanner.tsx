'use client'

import { useState, useEffect } from 'react'
import { AlertTriangle, X, Server } from 'lucide-react'

export function ColdStartBanner() {
  const [showModal, setShowModal] = useState(false)
  const [countdown, setCountdown] = useState(50)
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    // Check if user has already dismissed this session
    const hasDismissed = sessionStorage.getItem('coldstart_dismissed')
    if (!hasDismissed) {
      setShowModal(true)
    }
  }, [])

  // Countdown timer
  useEffect(() => {
    if (!showModal || countdown <= 0) return
    
    const timer = setInterval(() => {
      setCountdown(prev => prev - 1)
    }, 1000)
    
    return () => clearInterval(timer)
  }, [showModal, countdown])

  const handleDismiss = () => {
    setShowModal(false)
    setDismissed(true)
    sessionStorage.setItem('coldstart_dismissed', 'true')
  }

  if (!showModal || dismissed) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-nano-card border border-nano-border rounded-2xl max-w-md w-full p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <Server className="w-5 h-5 text-nano-accent" />
            <h2 className="text-lg font-semibold text-nano-accent">
              Server Cold Start
            </h2>
          </div>
          <button 
            onClick={handleDismiss}
            className="p-1 hover:bg-nano-border rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-nano-muted" />
          </button>
        </div>

        {/* Warning Box */}
        <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl mb-5">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-amber-400 font-semibold text-sm mb-1">
              Free Tier Deployment Notice
            </p>
            <p className="text-nano-muted text-sm">
              This backend is deployed on a free tier service (Render) that goes to sleep after 15 minutes of inactivity.
            </p>
          </div>
        </div>

        {/* Info Text */}
        <div className="text-sm text-nano-muted space-y-3 mb-5">
          <p>
            <span className="text-nano-text font-semibold">First request may take 30-50 seconds</span>
            {' '}while the server wakes up. This is normal behavior for free tier deployments.
          </p>
          <p>
            Subsequent requests will be fast until the server goes idle again.
          </p>
        </div>

        {/* Countdown Timer */}
        {countdown > 0 && (
          <div className="bg-nano-bg rounded-xl p-4 text-center mb-5">
            <p className="text-nano-muted text-sm mb-1">Server warming up...</p>
            <p className="text-3xl font-light text-nano-text mb-1">{countdown}s</p>
            <p className="text-nano-muted text-sm">Please wait before retrying</p>
          </div>
        )}

        {/* Footer Button */}
        <button
          onClick={handleDismiss}
          className="w-full px-4 py-3 bg-nano-accent hover:bg-nano-accent-hover 
                     rounded-xl text-white font-medium transition-colors"
        >
          Got it, I'll wait
        </button>
      </div>
    </div>
  )
}
