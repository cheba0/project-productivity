export interface ProjectSprint {
  number: number
  start: string
  end: string
}

export interface ProjectSprints {
  items: ProjectSprint[]
  current_sprint: number | null
}

export interface DashboardTask {
  id: number
  title: string
  status: string
  done: boolean
  assigned_to: number | null
  estimated_hours: number | null
  spent_hours: number
  start_date: string | null
  due_date: string | null
}

export interface ProjectDashboard {
  period: {
    start: string
    end: string
  }
  sources: {
    gitlab: 'live' | 'not_configured'
    redmine: 'live' | 'not_configured'
  }
  summary: {
    tasks_total: number
    tasks_done: number
    tasks_in_progress: number
    progress_percent: number | null
    commits: number
    actual_hours: number
    planned_hours: number | null
    last_gitlab_activity: string | null
    last_redmine_activity: string | null
  }
  tasks: DashboardTask[]
}

export type DashboardPeriod =
  | { sprint: number }
  | { start: string; end: string }

async function readResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)

    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : `Не удалось загрузить данные: HTTP ${response.status}`,
    )
  }

  return response.json()
}

export async function getProjectSprints(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectSprints> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}/sprints`,
    {
      credentials: 'include',
      signal,
    },
  )

  return readResponse<ProjectSprints>(response)
}

export async function getProjectDashboard(
  projectId: string,
  period: DashboardPeriod,
  signal?: AbortSignal,
): Promise<ProjectDashboard> {
  const params = new URLSearchParams()

  if ('sprint' in period) {
    params.set('sprint', String(period.sprint))
  } else {
    params.set('start', period.start)
    params.set('end', period.end)
  }

  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}/dashboard?${params}`,
    {
      credentials: 'include',
      signal,
    },
  )

  return readResponse<ProjectDashboard>(response)
}