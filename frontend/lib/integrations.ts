/**
 * Integrations API client for OAuth connections
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765'

export interface IntegrationsStatus {
  gmail: boolean
  calendar: boolean
  oauth_configured: boolean
}

/**
 * Get status of all integrations for the current user
 */
export async function getIntegrationsStatus(token: string): Promise<IntegrationsStatus> {
  const response = await fetch(`${API_BASE}/integrations/status?token=${token}`)
  
  if (!response.ok) {
    throw new Error(`Failed to get status: ${response.status}`)
  }
  
  return response.json()
}

/**
 * Get OAuth URL for connecting a service
 */
export async function connectService(token: string, service: 'gmail' | 'calendar' | 'all'): Promise<string> {
  const response = await fetch(`${API_BASE}/integrations/connect/${service}?token=${token}`)
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `Failed to connect: ${response.status}`)
  }
  
  const data = await response.json()
  return data.auth_url
}

/**
 * Disconnect a service
 */
export async function disconnectService(token: string, service: 'gmail' | 'calendar'): Promise<boolean> {
  const response = await fetch(`${API_BASE}/integrations/disconnect/${service}?token=${token}`, {
    method: 'DELETE',
  })
  
  if (!response.ok) {
    throw new Error(`Failed to disconnect: ${response.status}`)
  }
  
  const data = await response.json()
  return data.success
}
