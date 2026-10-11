const API_URL = 'http://localhost:8000'

export function login(): void {
  window.location.assign(`${API_URL}/auth/tpu/login`)
}


export async function getCurrentUser() {
  const response = await fetch(`${API_URL}/auth/me`, {
    credentials: 'include',
  })

  if (response.status === 401) {
    return null
  }

  if (!response.ok) {
    throw new Error('Не удалось проверить сессию')
  }

  return response.json()
}


export async function logout() {
  const response = await fetch(`${API_URL}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error('Не удалось выйти')
  }

  return response.json()
}