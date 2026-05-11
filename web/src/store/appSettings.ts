import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppSettings {
  fundCacheMinutes: number
  setFundCacheMinutes: (v: number) => void
}

export const useAppSettings = create<AppSettings>()(
  persist(
    (set) => ({
      fundCacheMinutes: 2,
      setFundCacheMinutes: (v) => set({ fundCacheMinutes: v }),
    }),
    { name: 'app-settings' }
  )
)
