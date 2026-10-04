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

  login: () => Promise<void>
  checkAuth: () => Promise<void>
  logout: () => Promise<void>
}


export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,


  login: async () => {
    set({ isLoading: true })

    try {
      await apiLogin()

      const user = await getCurrentUser()

      set({
        user,
        isAuthenticated: user !== null,
        isLoading: false,
      })
    } catch (error) {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      })

      throw error
    }
  },


  checkAuth: async () => {
    set({ isLoading: true })

    const user = await getCurrentUser()

    set({
      user,
      isAuthenticated: user !== null,
      isLoading: false,
    })
  },


  logout: async () => {
    await apiLogout()

    set({
      user: null,
      isAuthenticated: false,
    })
  },
}))