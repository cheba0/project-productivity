import { useEffect, useState } from 'react'

import {
  getAnalyticsProjects,
  type AnalyticsProject,
} from '../../../entities/project'

import { AnalyticsProjectCard } from './AnalyticsProjectCard'
import styles from './ProjectsPage.module.css'

export function AnalyticsProjectsSection() {
  const [projects, setProjects] = useState<AnalyticsProject[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    getAnalyticsProjects(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setProjects(result)
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error
              ? reason.message
              : 'Не удалось загрузить серверные проекты.',
          )
        }
      })

    return () => controller.abort()
  }, [reload])

  function refresh() {
    setProjects(null)
    setError(null)
    setReload((value) => value + 1)
  }

  const loading = projects === null && error === null

  return (
    <section
      className={styles.analyticsSection}
      aria-labelledby="analytics-projects-title"
    >
      <div className={styles.titleRow}>
        <div>
          <h2 id="analytics-projects-title">Проекты Analytics</h2>
          <p className={styles.subtitle}>
            Сохранённые показатели с сервера
          </p>
        </div>

        <button
          className="button"
          type="button"
          disabled={loading}
          onClick={refresh}
        >
          {loading ? 'Загрузка…' : 'Обновить'}
        </button>
      </div>

      {error && (
        <p role="alert" className={styles.message}>
          {error}
        </p>
      )}

      {projects?.length === 0 && (
        <p className={styles.message}>
          Серверных проектов пока нет.
        </p>
      )}

      {projects && (
        <div className={styles.grid}>
          {projects.map((project) => (
            <AnalyticsProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </section>
  )
}