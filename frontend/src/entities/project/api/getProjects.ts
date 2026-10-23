import type { Project } from '../model/types'

interface ProjectDto {
  id: string
  name: string
  gitlab_project_id: number | null
  redmine_project_id: number | null
}

export async function getProjects(signal: AbortSignal): Promise<Project[]> {
  const response = await fetch('/analytics/projects', { signal })
  if (!response.ok)
    throw new Error(`Не удалось загрузить проекты (HTTP ${response.status})`)
  const data: ProjectDto[] = await response.json()
  if (!Array.isArray(data))
    throw new Error('API вернул неожиданный формат проектов')
  return data.map((project) => ({
    id: project.id,
    name: project.name,
    gitlabProjectId: project.gitlab_project_id,
    redmineProjectId: project.redmine_project_id,
  }))
}
