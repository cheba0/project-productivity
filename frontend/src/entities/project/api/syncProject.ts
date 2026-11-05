export interface ProjectSyncStatus {
  project_id: string
  configured: boolean
  state:
    | 'not_configured'
    | 'never_synced'
    | 'needs_refresh'
    | 'ready'
    | 'error'
  has_cached_data: boolean
  last_attempt_at: string | null
  last_success_at: string | null
  last_error: string | null
  period: {
    start: string
    end: string
  } | null
  sync_interval_seconds: number
}

export async function syncProject(
  projectId: string,
): Promise<ProjectSyncStatus> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}/sync`,
    {
      method: 'POST',
      credentials: 'include',
    },
  )

  const body = await response.json()

  if (!response.ok) {
    const detail = body?.detail

    const message =
      typeof detail === 'string'
        ? detail
        : typeof detail?.message === 'string'
          ? detail.message
          : `Не удалось обновить данные: HTTP ${response.status}`

    throw new Error(message)
  }

  return body
}

export async function getProjectSyncStatus(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectSyncStatus> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}/sync-status`,
    {
      credentials: 'include',
      signal,
    },
  )

  const body = await response.json()

  if (!response.ok) {
    const detail = body?.detail

    throw new Error(
      typeof detail === 'string'
        ? detail
        : typeof detail?.message === 'string'
          ? detail.message
          : `Не удалось проверить состояние данных: HTTP ${response.status}`,
    )
  }

  return body
}