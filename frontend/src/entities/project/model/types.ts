export type ProjectCategory = 'active' | 'paused' | 'archived'
export type ActivityStatus = 'working' | 'slowing' | 'idle'

export interface Project {
  id: string
  name: string
  category?: ProjectCategory
  activity?: ActivityStatus
  members?: number
  gitlabProjectId: number | null
  redmineProjectId: number | null
  gitlabDaysAgo?: number
  redmineDaysAgo?: number
  deadline?: string
  progress?: number
  archivedAt?: string
  startedAt?: string
  tasksCompleted?: number
  tasksTotal?: number
  actualHours?: number
  plannedHours?: number
}

export const activityLabels: Record<ActivityStatus, string> = {
  working: 'Идёт работа',
  slowing: 'Замедление',
  idle: 'Простой',
}
