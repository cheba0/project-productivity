import type { User } from '../types/auth'


const API_URL = ''

export function login(): void {
  window.location.assign(`${API_URL}/auth/tpu/login`)
}


export async function getCurrentUser(): Promise<User | null> {
  const response = await fetch(`${API_URL}/auth/me`, {
    credentials: 'include',
  })

  if (response.status === 401) {
    return null
  }

  return response.json() as Promise<User>
}


export async function logout(): Promise<void> {
  await fetch(`${API_URL}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })
}
