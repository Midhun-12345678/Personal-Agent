'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Bot, ArrowRight, Lock, User } from 'lucide-react'
import { registerUser, loginUser, checkUserExists } from '@/lib/api'

export default function Home() {
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [userExists, setUserExists] = useState<boolean | null>(null)
  const [checkingUser, setCheckingUser] = useState(false)
  const router = useRouter()

  // Check if user exists when name changes (debounced)
  useEffect(() => {
    if (!name.trim()) {
      setUserExists(null)
      return
    }

    const timer = setTimeout(async () => {
      setCheckingUser(true)
      try {
        const exists = await checkUserExists(name.trim())
        setUserExists(exists)
      } catch {
        setUserExists(null)
      } finally {
        setCheckingUser(false)
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [name])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    setLoading(true)
    setError('')

    try {
      let response
      if (userExists) {
        // Existing user - login
        if (!password) {
          setError('Please enter your password')
          setLoading(false)
          return
        }
        response = await loginUser(name.trim(), password)
      } else {
        // New user - register
        response = await registerUser(name.trim(), password || undefined)
      }

      // Clear old messages from any previous session
      localStorage.removeItem('nanobot_messages')
      localStorage.setItem('nanobot_token', response.token)
      localStorage.setItem('nanobot_user_id', response.user_id)
      localStorage.setItem('nanobot_name', name.trim())
      router.push('/chat')
    } catch (err: any) {
      setError(err.message || 'Failed to connect. Make sure the backend is running.')
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-nano-accent/20 mb-4">
            <Bot className="w-8 h-8 text-nano-accent" />
          </div>
          <h1 className="text-3xl font-bold text-nano-text mb-2">
            Welcome to YourBot
          </h1>
          <p className="text-nano-muted">
            Your personal AI automation assistant.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-nano-muted" />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your name"
              className="w-full pl-10 pr-4 py-3 bg-nano-card border border-nano-border rounded-xl 
                         text-nano-text placeholder-nano-muted focus:outline-none 
                         focus:border-nano-accent transition-colors"
              disabled={loading}
            />
            {checkingUser && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-nano-muted/30 border-t-nano-muted rounded-full animate-spin" />
            )}
          </div>

          {/* Show password field for existing users or as optional for new users */}
          {name.trim() && (
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-nano-muted" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={userExists ? "Enter your password" : "Create a password (optional)"}
                className="w-full pl-10 pr-4 py-3 bg-nano-card border border-nano-border rounded-xl 
                           text-nano-text placeholder-nano-muted focus:outline-none 
                           focus:border-nano-accent transition-colors"
                disabled={loading}
              />
            </div>
          )}

          {/* Status message */}
          {name.trim() && userExists !== null && !checkingUser && (
            <p className={`text-sm text-center ${userExists ? 'text-nano-accent' : 'text-green-500'}`}>
              {userExists ? 'Welcome back! Enter your password to continue.' : 'New user - you can set a password to secure your account.'}
            </p>
          )}

          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={!name.trim() || loading || (userExists === true && !password)}
            className="w-full flex items-center justify-center gap-2 px-4 py-3
                       bg-nano-accent hover:bg-nano-accent-hover disabled:opacity-50
                       disabled:cursor-not-allowed rounded-xl text-white font-medium
                       transition-colors"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                {userExists ? 'Login' : 'Get Started'}
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        <p className="text-center text-nano-muted text-sm mt-6">
          By continuing, you agree to let YourBot remember information to help you better.
        </p>
      </div>
    </main>
  )
}
