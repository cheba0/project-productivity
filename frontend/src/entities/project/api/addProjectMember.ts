import type { ProjectDto } from './getProjects'

export async function addProjectMember(
  projectId: string,
  payload: { email: string; role: string },
): Promise<ProjectDto['members'][number]> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}/members`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    },
  )

  const body = await response.json().catch(() => null)

  if (!response.ok) {
    if (response.status === 409) {
      throw new Error('Участник с такой почтой уже добавлен.')
    }

    if (response.status === 403) {
      throw new Error('Добавлять участников может владелец проекта.')
    }

    if (response.status === 401) {
      throw new Error('Сессия истекла. Войдите снова.')
    }

    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : 'Не удалось добавить участника. Проверьте введённые данные.',
    )
  }

  return body
}