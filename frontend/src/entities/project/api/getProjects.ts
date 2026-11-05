export type ProjectFilter = 'active' | 'paused' | 'archived'

export interface ProjectDto {
  id: string
  workspace_id: string
  name: string
  showcase_url: string | null
  gitlab_url: string | null
  redmine_url: string | null
  gitlab_token_configured: boolean
  redmine_token_configured: boolean
  sprint_weeks: number
  active_after_days: number
  delayed_after_days: number
  start_date: string | null
  deadline: string | null
  is_paused: boolean
  archived_at: string | null
  status: string
  status_label: string
  progress_percent: number | null
  tasks_done: number | null
  tasks_total: number | null
  gitlab_inactive_days: number | null
  redmine_inactive_days: number | null
  commits_per_day: number[] | null
  members: {
    id: string
    email: string
    name: string | null
    role: string
    is_owner: boolean
    is_pending: boolean
  }[]
  created_at: string
  updated_at: string
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