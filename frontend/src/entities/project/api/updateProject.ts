import type {ProjectDto} from './getProjects'

export interface ProjectUpdate {
  name?: string
  showcase_url?: string | null
  gitlab_url?: string | null
  redmine_url?: string | null
  gitlab_token?: string
  redmine_token?: string
  sprint_weeks?: number
  active_after_days?: number
  delayed_after_days?: number
  start_date?: string | null
  deadline?: string | null
}

function errorMessage(body: unknown, status: number): string {
  if (status === 401) return 'Сессия истекла. Войдите снова.'
  if (status === 403) return 'Настройки может менять только владелец проекта.'
  if (status === 404) return 'Проект не найден или недоступен.'

  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = body.detail

    if (typeof detail === 'string') return detail

    if (Array.isArray(detail)) {
      const messages = detail.map((item: unknown) => {
        if (!item || typeof item !== 'object' || !('msg' in item)) return null
        return typeof item.msg === 'string' ? item.msg : null
      }).filter(Boolean)

      if (messages.length) return messages.join('. ')
    }
  }

  return `Не удалось сохранить настройки: HTTP ${status}`
}

export async function updateProject(projectId: string, payload: ProjectUpdate): Promise<ProjectDto> {
  const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
    method: 'PATCH',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  })

  const body: unknown = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(errorMessage(body, response.status))
  }

  return body as ProjectDto
}