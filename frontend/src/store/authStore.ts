import { create } from 'zustand'

import type { User } from '../types/auth'

import {
  login as apiLogin,
  getCurrentUser,
  logout as apiLogout,
} from '../api/authApi'


interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean

  login: () => void
  checkAuth: () => Promise<void>
  logout: () => Promise<void>
}


export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,


  login: () => {
    set({ isLoading: true })
    apiLogin()
  },


  checkAuth: async () => {
    set({ isLoading: true })

    try {
      const user = await getCurrentUser()

      set({
        user,
        isAuthenticated: user !== null,
        isLoading: false,
      })
    } catch {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      })
    }
  },


  logout: async () => {
    await apiLogout()

    set({
      user: null,
      isAuthenticated: false,
    })
  },
}))