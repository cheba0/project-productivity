export interface AnalyticsProject {
  id: string
  name: string
  gitlab_project_id: number | null
  redmine_project_id: number | null
}

export interface AnalyticsProjectMetrics {
  project_id: string
  project_name: string
  metrics: {
    closed_tasks?: number
    completion_rate?: number
    estimated_hours?: number
    non_merge_commits?: number
    open_tasks?: number
    task_spent_hours?: number
    total_additions?: number
    total_commits?: number
    total_deletions?: number
    total_tasks?: number
  }
}

async function readResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(
      `Не удалось получить данные Analytics: HTTP ${response.status}`,
    )
  }

  return response.json()
}

export async function getAnalyticsProjects(
  signal?: AbortSignal,
): Promise<AnalyticsProject[]> {
  const response = await fetch('/analytics/projects', { signal })

  return readResponse<AnalyticsProject[]>(response)
}

export async function getAnalyticsProjectMetrics(
  projectId: string,
  signal?: AbortSignal,
): Promise<AnalyticsProjectMetrics> {
  const response = await fetch(
    `/analytics/projects/${encodeURIComponent(projectId)}/metrics`,
    { signal },
  )

  return readResponse<AnalyticsProjectMetrics>(response)
}