import {create} from 'zustand'
import {getProjects} from '../entities/project'
import {syncProject} from '../entities/project/api/syncProject'

interface ProjectSyncState {
  syncing: boolean
  message: string | null
  errors: string[]
  revision: number
  invalidateProjects: () => void
  syncOwnedProjects: (email: string) => Promise<void>
}

export const useProjectSyncStore = create<ProjectSyncState>((set, get) => ({
  syncing: false,
  message: null,
  errors: [],
  revision: 0,

  invalidateProjects: () => {
    set((state) => ({revision: state.revision + 1}))
  },

  syncOwnedProjects: async (email) => {
    if (get().syncing) return

    set({syncing: true, message: 'Получаем список проектов…', errors: []})

    try {
      const response = await getProjects('active')
      const normalizedEmail = email.trim().toLowerCase()
      const projects = response.items.filter((project) =>
        project.members.some((member) => member.is_owner && member.email.trim().toLowerCase() === normalizedEmail),
      )

      if (!projects.length) {
        set({message: 'Нет активных проектов, которыми вы владеете.'})
        return
      }

      let completed = 0
      const errors: string[] = []

      for (const [index, project] of projects.entries()) {
        set({message: `Обновляем ${index + 1} из ${projects.length}: ${project.name}`})

        try {
          const result = await syncProject(project.id)

          if (result.state === 'error' || !result.has_cached_data) {
            throw new Error(result.last_error ?? 'Данные не удалось обновить.')
          }

          completed += 1
        } catch (reason: unknown) {
          const message = reason instanceof Error ? reason.message : 'Не удалось обновить данные.'
          errors.push(`${project.name}: ${message}`)
        }
      }

      set({message: `Обновлено проектов: ${completed} из ${projects.length}.`, errors})
    } catch (reason: unknown) {
      set({
        message: null,
        errors: [reason instanceof Error ? reason.message : 'Не удалось запустить обновление.'],
      })
    } finally {
      set((state) => ({syncing: false, revision: state.revision + 1}))
    }
  },
}))