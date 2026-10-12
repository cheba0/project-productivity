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

  login: () => void
  checkAuth: () => Promise<void>
  logout: () => Promise<void>
}


export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,


  login: () => {
    set({ isLoading: true })
    apiLogin()
  },


  checkAuth: async () => {
    set({ isLoading: true })

    const user = await getCurrentUser().catch(() => null)
    set({ user, isLoading: false })
  },


  logout: async () => {
    await apiLogout()

    set({ user: null })
  },
}))
