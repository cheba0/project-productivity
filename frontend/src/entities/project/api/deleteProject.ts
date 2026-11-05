export async function deleteProject(projectId: string, name: string): Promise<void> {
  const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name}),
  })

  if (response.ok) return

  const body = await response.json().catch(() => null)

  if (response.status === 401) {
    throw new Error('Сессия истекла. Войдите снова.')
  }

  if (response.status === 403) {
    throw new Error('Удалить проект может только его владелец.')
  }

  if (response.status === 404) {
    throw new Error('Проект не найден или больше недоступен.')
  }

  if (response.status === 409) {
    throw new Error('Название не совпадает. Возможно, проект был переименован — обновите страницу.')
  }

  throw new Error(
    typeof body?.detail === 'string'
      ? body.detail
      : `Не удалось удалить проект: HTTP ${response.status}`,
  )
}