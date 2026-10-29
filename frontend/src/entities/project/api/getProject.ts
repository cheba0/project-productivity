import type { ProjectDto } from './getProjects'

export async function getProject(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectDto> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}`,
    {
      credentials: 'include',
      signal,
    },
  )

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Проект не найден или у вас нет доступа.')
    }

    if (response.status === 401) {
      throw new Error('Сессия истекла. Войдите в приложение снова.')
    }

    throw new Error(
      `Не удалось загрузить проект: HTTP ${response.status}`,
    )
  }

  return response.json()
}