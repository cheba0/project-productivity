import { create } from 'zustand'

import type { User } from '../types/auth'
import {
  login as apiLogin,
  getCurrentUser,
  logout as apiLogout,
} from '../api/authApi'

interface AuthState {
  user: User | null
  isLoading: boolean
  error: string | null

  checkAuth: () => Promise<void>
  logout: () => Promise<void>
}

let authCheck: Promise<void> | null = null

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  error: null,

  checkAuth: () => {
    if (authCheck) return authCheck

    authCheck = (async () => {
      set({ isLoading: true, error: null })

      const params = new URLSearchParams(window.location.search)

      if (params.has('auth_error')) {
        set({
          user: null,
          isLoading: false,
          error: 'Не удалось пройти авторизацию через ТПУ.',
        })
        return
      }

      try {
        const user = await getCurrentUser()

        if (!user) {
          apiLogin()
          return
        }

        set({
          user,
          isLoading: false,
          error: null,
        })
      } catch {
        set({
          user: null,
          isLoading: false,
          error: 'Не удалось проверить сессию. Проверьте подключение к серверу.',
        })
      }
    })().finally(() => {
      authCheck = null
    })

    return authCheck
  },

  logout: async () => {
    await apiLogout()

    set({
      user: null,
      error: null,
      isLoading: true,
    })

    apiLogin()
  },
}))