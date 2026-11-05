import type {ProjectDto} from './getProjects'

export async function setProjectArchived(projectId: string, archived: boolean): Promise<ProjectDto> {
  const action = archived ? 'archive' : 'restore'
  const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}/${action}`, {
    method: 'POST',
    credentials: 'include',
  })

  const body = await response.json().catch(() => null)

  if (!response.ok) {
    if (response.status === 401) throw new Error('Сессия истекла. Войдите снова.')
    if (response.status === 403) throw new Error('Это действие доступно только владельцу проекта.')
    if (response.status === 404) throw new Error('Проект не найден или недоступен.')

    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : `Не удалось изменить состояние проекта: HTTP ${response.status}`,
    )
  }

  return body
}