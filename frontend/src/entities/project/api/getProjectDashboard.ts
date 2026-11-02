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

export interface ProjectDeadlines {
  available: boolean
  reason: string | null
  as_of: string
  window_days: number
  items: {
    id: number
    title: string | null
    status: string
    due_date: string
    days_remaining: number
    overdue: boolean
    assigned_to: number | null
    estimated_hours: number | null
  }[]
  total_matching: number
  known_due_date_tasks: number
  open_tasks_without_due_date: number
}

export interface ProjectSprintHours {
  available: boolean
  reason: string | null
  plan_basis: string
  unallocated_plan_hours?: number | null
  unallocated_estimated_tasks?: number
  items: {
    sprint: number
    start: string
    end: string
    visible_start: string
    visible_end: string
    partial_period: boolean
    planned_hours: number | null
    actual_hours: number | null
    deviation_hours: number | null
    estimated_tasks: number
    time_entries: number | null
  }[]
}

export interface ProjectPlanningQuality {
  counts: {
    normal: number
    warning: number
    error: number
    unplanned: number
  }
  total: number
  percentages: {
    normal: number | null
    warning: number | null
    error: number | null
    unplanned: number | null
  }
}

export interface DashboardStudent {
  member_id: string
  name: string | null
  email: string
  role: string
  redmine_user_id: number | null
  actual_hours: number | null
  planned_hours: number | null
  hours_deviation_percent: number | null
  gitlab_inactive_days: number | null
  redmine_inactive_days: number | null
  activity_status: string
}

export interface ProjectDashboard {
  period: {
    start: string
    end: string
  }
  sources: {
    gitlab: 'cached' | 'database' | 'live' | 'not_configured'
    redmine: 'cached' | 'database' | 'live' | 'not_configured'
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
  upcoming_deadlines: ProjectDeadlines
  sprint_hours: ProjectSprintHours
  planning_quality: ProjectPlanningQuality
  students: DashboardStudent[]
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