import type { MemberProfile } from './updateMemberProfile'

export interface MemberDashboard {
  profile: MemberProfile
  period: {
    start: string
    end: string
  }
  sources: {
    gitlab: 'cached' | 'database' | 'live' | 'not_configured'
    redmine: 'cached' | 'database' | 'live' | 'not_configured'
  }
  summary: {
    commits: number
    redmine_entries: number | null
    actual_hours: number | null
    planned_hours: number | null
    hours_deviation: number | null
    hours_deviation_percent: number | null
    tasks_total: number | null
    tasks_done: number | null
    tasks_in_progress: number | null
    gitlab_inactive_days: number | null
    redmine_inactive_days: number | null
    activity_status: string
    active_weeks: number
  }
  daily_activity: {
    date: string
    gitlab_commits: number
    redmine_updates: number | null
    redmine_hours: number | null
    activity_kind: string
    is_weekend: boolean
  }[]
}

export async function getMemberDashboard(
  projectId: string,
  memberId: string,
  period: { start: string; end: string },
  signal?: AbortSignal,
): Promise<MemberDashboard> {
  const params = new URLSearchParams(period)

  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}` +
      `/members/${encodeURIComponent(memberId)}/dashboard?${params}`,
    {
      credentials: 'include',
      signal,
    },
  )

  const body = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : typeof body?.detail?.message === 'string'
          ? body.detail.message
          : `Не удалось загрузить участника: HTTP ${response.status}`,
    )
  }

  return body
}