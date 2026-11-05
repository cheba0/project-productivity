export async function removeProjectMember(projectId: string, memberId: string): Promise<void> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}/members/${encodeURIComponent(memberId)}`,
    {method: 'DELETE', credentials: 'include'},
  )

  if (response.ok) return

  const body = await response.json().catch(() => null)

  if (response.status === 401) {
    throw new Error('Сессия истекла. Войдите снова.')
  }

  if (response.status === 403) {
    throw new Error('Удалять участников может владелец проекта. Владельца удалить нельзя.')
  }

  if (response.status === 404) {
    throw new Error('Участник или проект больше недоступен. Обновите страницу.')
  }

  throw new Error(
    typeof body?.detail === 'string'
      ? body.detail
      : `Не удалось удалить участника: HTTP ${response.status}`,
  )
}