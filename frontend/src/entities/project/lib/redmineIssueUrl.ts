export function redmineIssueUrl(projectUrl: string | null | undefined, issueId: number): string | null {
  if (!projectUrl || !Number.isInteger(issueId) || issueId <= 0) return null

  try {
    const url = new URL(projectUrl)

    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return null

    const path = url.pathname.replace(/\/+$/, '')
    const projectIndex = path.indexOf('/projects/')
    const prefix = projectIndex >= 0 ? path.slice(0, projectIndex) : path

    url.pathname = `${prefix}/issues/${issueId}`
    url.search = ''
    url.hash = ''

    return url.href
  } catch {
    return null
  }
}