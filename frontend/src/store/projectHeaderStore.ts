import { create } from 'zustand'

interface ProjectHeaderState {
  controlsElement: HTMLDivElement | null
  setControlsElement: (element: HTMLDivElement | null) => void
}

export const useProjectHeaderStore = create<ProjectHeaderState>(
  (set) => ({
    controlsElement: null,

    setControlsElement: (controlsElement) => {
      set({ controlsElement })
    },
  }),
)