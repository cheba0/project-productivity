import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import {
  getProject,
  getProjectLiveCard,
  type ProjectDto,
  type ProjectLiveCard,
} from '../../../entities/project'

import styles from './ProjectPage.module.css'

function formatDate(value: string): string {
  const date = new Date(
    value.includes('T') ? value : `${value}T00:00:00`,
  )

  return new Intl.DateTimeFormat('ru-RU').format(date)
}

export function ProjectPage() {
  const { projectId } = useParams()

  // При переходе между проектами сбрасываем состояние содержимого.
  return projectId ? (
    <ProjectContent key={projectId} projectId={projectId} />
  ) : (
    <p role="alert">Не указан идентификатор проекта.</p>
  )
}

function ProjectContent({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<ProjectDto | null>(null)
  const [projectError, setProjectError] = useState<string | null>(null)

  const [metrics, setMetrics] = useState<ProjectLiveCard | null>(null)
  const [metricsError, setMetricsError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    getProject(projectId, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setProject(result)
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setProjectError(
            error instanceof Error
              ? error.message
              : 'Не удалось загрузить проект.',
          )
        }
      })

    return () => controller.abort()
  }, [projectId])

  useEffect(() => {
    if (!project) return

    const controller = new AbortController()

    getProjectLiveCard(project.id, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setMetrics(result)
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setMetricsError(
            error instanceof Error
              ? error.message
              : 'Не удалось загрузить показатели.',
          )
        }
      })

    return () => controller.abort()
  }, [project, reload])

  function refreshMetrics() {
    setMetrics(null)
    setMetricsError(null)
    setReload((value) => value + 1)
  }

  if (projectError) {
    return (
      <section className={styles.page}>
        <Link to="/">← Проекты</Link>
        <p className={styles.error} role="alert">
          {projectError}
        </p>
      </section>
    )
  }

  if (!project) {
    return <p role="status">Загрузка проекта…</p>
  }

  const loadingMetrics = !metrics && !metricsError

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>{project.name}</h1>
          <p>
            {project.archived_at
              ? 'В архиве'
              : project.is_paused
                ? 'На паузе'
                : 'Активный проект'}
          </p>
        </div>

        <Link
          className="button"
          to={`/projects/${project.id}/settings`}
          state={{ projectName: project.name }}
        >
          Настройки проекта
        </Link>
      </header>

      <section className={styles.panel}>
        <h2>О проекте</h2>

        <dl className={styles.details}>
          <div>
            <dt>GitLab</dt>
            <dd>
              {project.gitlab_url ? (
                <a
                  href={project.gitlab_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Открыть репозиторий
                </a>
              ) : (
                'Не подключён'
              )}
            </dd>
          </div>

          <div>
            <dt>Redmine</dt>
            <dd>
              {project.redmine_url ? (
                <a
                  href={project.redmine_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Открыть проект
                </a>
              ) : (
                'Не подключён'
              )}
            </dd>
          </div>

          <div>
            <dt>Дата начала</dt>
            <dd>
              {project.start_date
                ? formatDate(project.start_date)
                : 'Не указана'}
            </dd>
          </div>

          <div>
            <dt>Срок завершения</dt>
            <dd>
              {project.deadline
                ? formatDate(project.deadline)
                : 'Не указан'}
            </dd>
          </div>
        </dl>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHeader}>
          <h2>Показатели за последние 30 дней</h2>

          <button
            className="button"
            type="button"
            disabled={loadingMetrics}
            onClick={refreshMetrics}
          >
            Обновить
          </button>
        </div>

        {loadingMetrics && (
          <p role="status">Получаем данные интеграций…</p>
        )}

        {metricsError && (
          <p className={styles.error} role="alert">
            {metricsError}
          </p>
        )}

        {metrics && (
          <>
            <p className={styles.muted}>
              {formatDate(metrics.period.start)} —{' '}
              {formatDate(metrics.period.end)}
            </p>

            <dl className={styles.metrics}>
              <div>
                <dt>Коммиты</dt>
                <dd>{metrics.summary.commits}</dd>
              </div>

              <div>
                <dt>Завершённые задачи</dt>
                <dd>
                  {metrics.summary.tasks_done} /{' '}
                  {metrics.summary.tasks_total}
                </dd>
              </div>

              <div>
                <dt>Прогресс</dt>
                <dd>
                  {metrics.summary.progress_percent === null
                    ? 'Нет данных'
                    : `${metrics.summary.progress_percent}%`}
                </dd>
              </div>

              <div>
                <dt>Фактические часы</dt>
                <dd>{metrics.summary.actual_hours}</dd>
              </div>
            </dl>

            {!project.redmine_url && (
              <p className={styles.muted}>
                Redmine не подключён. Нули в задачах и часах пока
                означают отсутствие данных этой интеграции.
              </p>
            )}
          </>
        )}
      </section>

      <section className={styles.panel}>
        <h2>Участники · {project.members.length}</h2>

        <ul className={styles.members}>
          {project.members.map((member) => (
            <li key={member.id}>
              <strong>{member.name || member.email}</strong>
              <span>
                {member.role === 'owner' ? 'Владелец' : member.role}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </section>
  )
}