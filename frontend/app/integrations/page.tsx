'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Mail, Calendar, Check, X, Loader2, AlertCircle, Link2 } from 'lucide-react'
import { getIntegrationsStatus, connectService, disconnectService, IntegrationsStatus } from '@/lib/integrations'

interface ServiceCardProps {
  name: string
  description: string
  icon: React.ReactNode
  connected: boolean
  loading: boolean
  oauthConfigured: boolean
  onConnect: () => void
  onDisconnect: () => void
}

function ServiceCard({
  name,
  description,
  icon,
  connected,
  loading,
  oauthConfigured,
  onConnect,
  onDisconnect,
}: ServiceCardProps) {
  return (
    <div className="bg-nano-card border border-nano-border rounded-xl p-6">
      <div className="flex items-start gap-4">
        <div className={`p-3 rounded-lg ${connected ? 'bg-green-500/20' : 'bg-nano-bg'}`}>
          {icon}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-nano-text">{name}</h3>
            {connected && (
              <span className="flex items-center gap-1 text-xs text-green-500 bg-green-500/10 px-2 py-0.5 rounded-full">
                <Check className="w-3 h-3" />
                Connected
              </span>
            )}
          </div>
          <p className="text-nano-muted text-sm mt-1">{description}</p>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-nano-border">
        {!oauthConfigured ? (
          <div className="flex items-center gap-2 text-amber-500 text-sm">
            <AlertCircle className="w-4 h-4" />
            <span>OAuth not configured. Add Google credentials to config.</span>
          </div>
        ) : connected ? (
          <button
            onClick={onDisconnect}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <X className="w-4 h-4" />
            )}
            Disconnect
          </button>
        ) : (
          <button
            onClick={onConnect}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-nano-accent text-white rounded-lg hover:bg-nano-accent/80 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Link2 className="w-4 h-4" />
            )}
            Connect
          </button>
        )}
      </div>
    </div>
  )
}

export default function IntegrationsPage() {
  const router = useRouter()
  const [status, setStatus] = useState<IntegrationsStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [connectingService, setConnectingService] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const token = typeof window !== 'undefined' ? localStorage.getItem('nanobot_token') : null

  useEffect(() => {
    if (!token) {
      router.push('/')
      return
    }

    fetchStatus()

    // Listen for OAuth success message from popup
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'oauth_success') {
        fetchStatus()
      }
    }
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [token, router])

  const fetchStatus = async () => {
    if (!token) return

    try {
      const data = await getIntegrationsStatus(token)
      setStatus(data)
      setError(null)
    } catch (err) {
      setError('Failed to load integrations status')
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async (service: 'gmail' | 'calendar') => {
    if (!token) return

    setConnectingService(service)
    setError(null)

    try {
      const authUrl = await connectService(token, service)
      // Open OAuth flow in popup
      const popup = window.open(
        authUrl,
        'oauth',
        'width=600,height=700,left=200,top=100'
      )

      // Poll for popup close
      const pollTimer = setInterval(() => {
        if (popup?.closed) {
          clearInterval(pollTimer)
          setConnectingService(null)
          fetchStatus()
        }
      }, 500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
      setConnectingService(null)
    }
  }

  const handleDisconnect = async (service: 'gmail' | 'calendar') => {
    if (!token) return

    setConnectingService(service)
    setError(null)

    try {
      await disconnectService(token, service)
      fetchStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect')
    } finally {
      setConnectingService(null)
    }
  }

  if (!token) return null

  return (
    <div className="min-h-screen bg-nano-bg">
      {/* Header */}
      <header className="border-b border-nano-border bg-nano-card">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <button
            onClick={() => router.push('/chat')}
            className="flex items-center gap-2 text-nano-muted hover:text-nano-text transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Chat
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-nano-text">Integrations</h1>
          <p className="text-nano-muted mt-1">
            Connect your accounts to enable AI-powered automation
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-400">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-nano-accent" />
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            <ServiceCard
              name="Gmail"
              description="Read, search, send, and draft emails on your behalf"
              icon={<Mail className={`w-6 h-6 ${status?.gmail ? 'text-green-500' : 'text-nano-muted'}`} />}
              connected={status?.gmail ?? false}
              loading={connectingService === 'gmail'}
              oauthConfigured={status?.oauth_configured ?? false}
              onConnect={() => handleConnect('gmail')}
              onDisconnect={() => handleDisconnect('gmail')}
            />

            <ServiceCard
              name="Google Calendar"
              description="Create, view, and manage your calendar events"
              icon={<Calendar className={`w-6 h-6 ${status?.calendar ? 'text-green-500' : 'text-nano-muted'}`} />}
              connected={status?.calendar ?? false}
              loading={connectingService === 'calendar'}
              oauthConfigured={status?.oauth_configured ?? false}
              onConnect={() => handleConnect('calendar')}
              onDisconnect={() => handleDisconnect('calendar')}
            />
          </div>
        )}

        {/* Instructions */}
        {!status?.oauth_configured && !loading && (
          <div className="mt-8 p-6 bg-nano-card border border-nano-border rounded-xl">
            <h2 className="text-lg font-semibold text-nano-text mb-4">
              Setting Up Google OAuth
            </h2>
            <ol className="space-y-3 text-sm text-nano-muted">
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-nano-accent/20 text-nano-accent flex items-center justify-center text-xs font-medium">1</span>
                <span>Go to <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-nano-accent hover:underline">Google Cloud Console</a> and create a new project</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-nano-accent/20 text-nano-accent flex items-center justify-center text-xs font-medium">2</span>
                <span>Enable the Gmail API and Google Calendar API</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-nano-accent/20 text-nano-accent flex items-center justify-center text-xs font-medium">3</span>
                <span>Create OAuth 2.0 credentials (Web application type)</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-nano-accent/20 text-nano-accent flex items-center justify-center text-xs font-medium">4</span>
                <span>Add <code className="px-1.5 py-0.5 bg-nano-bg rounded">http://localhost:8765/integrations/callback</code> as an authorized redirect URI</span>
              </li>
              <li className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-nano-accent/20 text-nano-accent flex items-center justify-center text-xs font-medium">5</span>
                <span>Add your Client ID and Client Secret to <code className="px-1.5 py-0.5 bg-nano-bg rounded">~/.personal-agent/config.json</code>:</span>
              </li>
            </ol>
            <pre className="mt-4 p-4 bg-nano-bg rounded-lg text-xs text-nano-text overflow-x-auto">
{`{
  "integrations": {
    "google": {
      "clientId": "YOUR_CLIENT_ID.apps.googleusercontent.com",
      "clientSecret": "YOUR_CLIENT_SECRET"
    }
  }
}`}
            </pre>
          </div>
        )}
      </main>
    </div>
  )
}
