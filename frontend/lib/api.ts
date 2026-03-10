const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8765'

export interface RegisterResponse {
  token: string
  user_id: string
}

export async function checkUserExists(name: string): Promise<boolean> {
  const response = await fetch(`${BACKEND_URL}/user/exists?name=${encodeURIComponent(name)}`)
  if (!response.ok) {
    return false
  }
  const data = await response.json()
  return data.exists
}

export async function registerUser(name: string, password?: string): Promise<RegisterResponse> {
  const response = await fetch(`${BACKEND_URL}/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ display_name: name, password: password || null }),
  })

  if (response.status === 409) {
    throw new Error('User already exists')
  }
  if (!response.ok) {
    throw new Error('Registration failed')
  }

  return response.json()
}

export async function loginUser(name: string, password: string): Promise<RegisterResponse> {
  const response = await fetch(`${BACKEND_URL}/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ display_name: name, password }),
  })

  if (!response.ok) {
    throw new Error('Invalid username or password')
  }

  return response.json()
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`)
    return response.ok
  } catch {
    return false
  }
}
