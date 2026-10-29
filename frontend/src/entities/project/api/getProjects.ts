export type ProjectFilter = 'active' | 'paused' | 'archived'

export interface ProjectDto {
  id: string
  name: string
  gitlab_url: string | null
  redmine_url: string | null
  active_after_days: number
  delayed_after_days: number
  start_date: string | null
  deadline: string | null
  is_paused: boolean
  archived_at: string | null
  members: {
    id: string
    email: string
    name: string | null
    role: string
  }[]
}

export interface ProjectListResponse {
  items: ProjectDto[]
  counts: {
    active: number
    paused: number
    archived: number
    all: number
  }
}

export async function getProjects(
  filter: ProjectFilter,
  signal?: AbortSignal,
): Promise<ProjectListResponse> {
  const response = await fetch(`/api/projects?filter=${filter}`, {
    credentials: 'include',
    signal,
  })

  if (!response.ok) {
    throw new Error(
      response.status === 401
        ? 'Сессия истекла. Войдите в приложение снова.'
        : `Не удалось загрузить проекты: HTTP ${response.status}`,
    )
  }

  return response.json()
}