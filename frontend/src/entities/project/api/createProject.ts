export interface CreateProjectInput {
  name: string
  showcase_url: string | null
  gitlab_url: string
  redmine_url: string | null
  gitlab_token: string
  redmine_token: string | null
  active_after_days: number
  delayed_after_days: number
  start_date: string | null
  deadline: string | null
  sprint_weeks: number
}

// Здесь описываем только поля ответа, которые нужны на этом этапе.
export interface CreatedProject {
  id: string
  name: string
}

export interface ProjectLiveCard {
  project_id: string
  name: string
  period: {
    start: string
    end: string
  }
  summary: {
    tasks_total: number
    tasks_done: number
    progress_percent: number | null
    commits: number
    actual_hours: number
    planned_hours: number | null
    last_gitlab_activity: string | null
    last_redmine_activity: string | null
  }
}

async function checkResponse(response: Response): Promise<void> {
  if (response.ok) return

  const body = await response.json().catch(() => null)

  if (typeof body?.detail === 'string') {
    throw new Error(body.detail)
  }

  if (response.status === 422) {
    throw new Error(
      'Проверьте поля формы: ссылки, название и пороги статусов.',
    )
  }

  if (response.status === 401) {
    throw new Error('Сессия истекла. Войдите в приложение снова.')
  }

  throw new Error(`Ошибка запроса: HTTP ${response.status}`)
}

export async function createProject(
  payload: CreateProjectInput,
): Promise<CreatedProject> {
  const response = await fetch('/api/projects', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  await checkResponse(response)

  return response.json()
}

export async function getProjectLiveCard(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectLiveCard> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}/live-card`,
    {
      credentials: 'include',
      signal,
    },
  )

  await checkResponse(response)
  return response.json()
}