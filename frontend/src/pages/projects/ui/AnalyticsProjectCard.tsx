import { useEffect, useState } from 'react'

import {
  getAnalyticsProjectMetrics,
  ProjectLoadingCard,
  type AnalyticsProject,
  type AnalyticsProjectMetrics,
} from '../../../entities/project'

import styles from './AnalyticsProjectCard.module.css'

const numberFormatter = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 2,
})

function formatNumber(value: number | undefined): string {
  return value === undefined ? '—' : numberFormatter.format(value)
}

export function AnalyticsProjectCard({
  project,
}: {
  project: AnalyticsProject
}) {
  const [data, setData] = useState<AnalyticsProjectMetrics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    getAnalyticsProjectMetrics(project.id, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setData(result)
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error
              ? reason.message
              : 'Ошибка загрузки метрик.',
          )
        }
      })

    return () => controller.abort()
  }, [project.id, reload])

  function retry() {
    setError(null)
    setData(null)
    setReload((value) => value + 1)
  }

  if (!data && !error) {
    return <ProjectLoadingCard name={project.name} />
  }

  const metrics = data?.metrics

  const hasRedmine = project.redmine_project_id !== null
  const hasGitlab = project.gitlab_project_id !== null

  const progress = hasRedmine
    ? metrics?.completion_rate
    : undefined

  return (
    <article className={styles.card}>
      <h3>{project.name}</h3>

      <span className={styles.badge}>Серверные данные</span>

      <p className={styles.source}>
        GitLab · {hasGitlab ? 'Подключён' : 'Не подключён'}
      </p>

      <p className={styles.source}>
        Redmine · {hasRedmine ? 'Подключён' : 'Не подключён'}
      </p>

      {error ? (
        <>
          <p className={styles.error} role="alert">
            {error}
          </p>

          <button className="button" type="button" onClick={retry}>
            Повторить
          </button>
        </>
      ) : metrics ? (
        <>
          <dl className={styles.metrics}>
            <div>
              <dt>Закрыто задач</dt>
              <dd>
                {hasRedmine
                  ? `${formatNumber(metrics.closed_tasks)} из ${formatNumber(metrics.total_tasks)}`
                  : '—'}
              </dd>
            </div>

            <div>
              <dt>Открыто задач</dt>
              <dd>
                {hasRedmine ? formatNumber(metrics.open_tasks) : '—'}
              </dd>
            </div>

            <div>
              <dt>Трудозатраты: факт / план</dt>
              <dd>
                {hasRedmine
                  ? `${formatNumber(metrics.task_spent_hours)} / ${formatNumber(metrics.estimated_hours)} ч`
                  : '—'}
              </dd>
            </div>

            <div>
              <dt>Коммиты</dt>
              <dd>
                {hasGitlab ? formatNumber(metrics.total_commits) : '—'}
              </dd>
            </div>
          </dl>

          <footer className={styles.footer}>
            <div className={styles.progressHeading}>
              <span>Выполнено</span>
              <strong>
                {progress === undefined
                  ? '—'
                  : `${formatNumber(progress)}%`}
              </strong>
            </div>

            {progress === undefined ? (
              <span className={styles.noData}>Нет данных о прогрессе</span>
            ) : (
              <progress
                className={styles.progress}
                max={100}
                value={Math.min(100, Math.max(0, progress))}
                aria-label={`Выполнено в проекте «${project.name}»`}
              />
            )}
          </footer>
        </>
      ) : null}
    </article>
  )
}