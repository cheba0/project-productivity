import type { DashboardTask } from '../api/getProjectDashboard'

export type TaskQuality =
  | 'normal'
  | 'warning'
  | 'error'
  | 'planned'

export function getTaskQuality(
  task: DashboardTask,
): TaskQuality | null {
  if (!task.done) return 'planned'

  const estimate = task.estimated_hours

  if (
    estimate === null ||
    !Number.isFinite(estimate) ||
    estimate <= 0 ||
    !Number.isFinite(task.spent_hours)
  ) {
    return null
  }

  const deviation = (task.spent_hours - estimate) / estimate

  if (deviation <= 0.1 + 1e-9) return 'normal'
  if (deviation <= 0.2 + 1e-9) return 'warning'

  return 'error'
}