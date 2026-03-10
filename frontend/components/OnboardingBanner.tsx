'use client'

import { Sparkles } from 'lucide-react'

interface OnboardingBannerProps {
  currentStep: number
  totalSteps: number
}

export default function OnboardingBanner({
  currentStep,
  totalSteps,
}: OnboardingBannerProps) {
  return (
    <div className="bg-nano-accent/10 border-b border-nano-accent/20 px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-nano-accent" />
          <span className="text-sm text-nano-accent">
            Getting to know you...
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {Array.from({ length: totalSteps }).map((_, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full transition-colors ${
                index < currentStep
                  ? 'bg-nano-accent'
                  : index === currentStep
                  ? 'bg-nano-accent/50'
                  : 'bg-nano-border'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
