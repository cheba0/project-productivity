const API_URL = 'http://localhost:8000'

export async function login() {
  const response = await fetch(
    `${API_URL}/auth/login`,
    {
      method: 'POST',
      credentials: 'include',
    }
  )

  if (!response.ok) {
    throw new Error('Login failed')
  }

  return response.json()
}


export async function getCurrentUser() {
  const response = await fetch(
    `${API_URL}/auth/me`,
    {
      credentials: 'include',
    }
  )

  if (!response.ok) {
    return null
  }

  return response.json()
}


export async function logout() {
  const response = await fetch(
    `${API_URL}/auth/logout`,
    {
      method: 'POST',
      credentials: 'include',
    }
  )

  if (!response.ok) {
    throw new Error('Logout failed')
  }

  return response.json()
}