import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { Settings } from 'lucide-react'

import {
  getProjectLiveCard,
  ProjectLoadingCard,
  type ProjectDto,
  type ProjectLiveCard,
} from '../../../entities/project'

import styles from './ProjectDataCard.module.css'

interface ProjectDataCardProps {
  project: ProjectDto
}

function daysAgo(value: string | null): number | null {
  if (!value) return null

  const timestamp = Date.parse(value)

  if (!Number.isFinite(timestamp)) return null

  return Math.max(
    0,
    Math.floor((Date.now() - timestamp) / 86_400_000),
  )
}

function sourceColor(
  days: number | null,
  project: ProjectDto,
): string {
  if (days === null) return 'unknown'
  if (days <= project.active_after_days) return 'green'
  if (days <= project.delayed_after_days) return 'yellow'
  return 'red'
}

function sourceText(
  url: string | null,
  days: number | null,
  source: 'gitlab' | 'redmine',
): string {
  if (!url) return 'Не подключён'

  if (days === null) {
    return source === 'gitlab'
      ? 'Нет коммитов за последние 30 дней'
      : 'Нет данных об активности'
  }

  return `${days} дн. назад`
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU').format(
    new Date(value.includes('T') ? value : `${value}T00:00:00`),
  )
}

function getInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}
export function ProjectDataCard({
  project,
}: ProjectDataCardProps) {
  const [data, setData] = useState<ProjectLiveCard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    getProjectLiveCard(project.id, controller.signal)
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
              : 'Не удалось загрузить данные проекта.',
          )
        }
      })

    return () => controller.abort()
  }, [project.id, reload])

  function retry() {
    setData(null)
    setError(null)
    setReload((value) => value + 1)
  }

  if (!data && !error) {
    return <ProjectLoadingCard name={project.name} />
  }

  const gitlabDays = daysAgo(
    data?.summary.last_gitlab_activity ?? null,
  )

  const redmineDays = daysAgo(
    data?.summary.last_redmine_activity ?? null,
  )

  const gitlabColor = sourceColor(gitlabDays, project)
  const redmineColor = sourceColor(redmineDays, project)

  // Пока не выводим общий статус активности:
  // правило для проекта с одной интеграцией ещё не согласовано.
  let statusLabel = 'Нет данных'
  let statusColor = 'unknown'

  if (project.archived_at) {
    statusLabel = 'В архиве'
  } else if (project.is_paused) {
    statusLabel = 'На паузе'
  } else if (error) {
    statusLabel = 'Нет связи'
  } else {
    const colors = [
      ...(project.gitlab_url ? [gitlabColor] : []),
      ...(project.redmine_url ? [redmineColor] : []),
    ]

    const hasUnknown = colors.some((color) => color === 'unknown')
    const hasGreen = colors.some((color) => color === 'green')
    const allGreen = colors.every((color) => color === 'green')
    const allRed = colors.every((color) => color === 'red')

    if (colors.length === 0 || hasUnknown) {
      statusLabel = 'Нет данных'
    } else if (allGreen) {
      statusLabel = 'Идёт работа'
      statusColor = 'green'
    } else if (hasGreen) {
      statusLabel = 'Частично'
      statusColor = 'yellow'
    } else if (allRed) {
      statusLabel = 'Без активности'
      statusColor = 'red'
    } else {
      statusLabel = 'Замедление'
      statusColor = 'orange'
    }
  }
  if (project.archived_at) {
    const summary = data?.summary

    return (
      <article className={`${styles.card} ${styles.archivedCard}`}>
        <header className={styles.header}>
          <h2>
            <Link
              className={styles.projectLink}
              to={`/projects/${project.id}`}
            >
              {project.name}
            </Link>
          </h2>
        </header>

        <span className={styles.badge}>
          В архиве с {formatDate(project.archived_at)}
        </span>

        <div className={styles.members}>
          <div className={styles.avatars} aria-hidden="true">
            {project.members.slice(0, 3).map((member, index) => (
              <span
                key={member.id}
                className={styles.avatar}
                data-color={index}
              >
                {getInitials(member.name || member.email)}
              </span>
            ))}
          </div>

          <span>Участников: {project.members.length}</span>
        </div>

        {error ? (
          <div className={styles.errorBlock}>
            <p className={styles.error} role="alert">
              {error}
            </p>

            <button
              className={styles.retryButton}
              type="button"
              onClick={retry}
            >
              Повторить загрузку
            </button>
          </div>
        ) : summary ? (
          <>
            <div className={styles.archiveDetails}>
              <p>
                Задачи: {summary.tasks_done} из {summary.tasks_total}
              </p>

              <p>
                Трудозатраты: факт {summary.actual_hours} / план{' '}
                {summary.planned_hours ?? '—'} ч
              </p>

              <p>
                Сроки:{' '}
                {project.start_date && project.deadline
                  ? `${formatDate(project.start_date)} — ${formatDate(project.deadline)}`
                  : project.start_date
                    ? `с ${formatDate(project.start_date)}`
                    : project.deadline
                      ? `до ${formatDate(project.deadline)}`
                      : 'не указаны'}
              </p>
            </div>

            <div className={styles.archiveProgress}>
              {summary.progress_percent === null ? (
                <div
                  className={styles.emptyProgress}
                  role="img"
                  aria-label="Прогресс: нет данных"
                />
              ) : (
                <progress
                  className={styles.progress}
                  max={100}
                  value={summary.progress_percent}
                  aria-label={`Прогресс проекта «${project.name}» за последние 30 дней`}
                />
              )}

              <span className={styles.periodNote}>
                Показатели за последние 30 дней
              </span>
            </div>
          </>
        ) : null}
      </article>
    )
  }
  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <h2>
          <Link
            className={styles.projectLink}
            to={`/projects/${project.id}`}
          >
            {project.name}
          </Link>
        </h2>

        <Link
          className={styles.settings}
          to={`/projects/${project.id}/settings`}
          state={{ projectName: project.name }}
          aria-label={`Настройки проекта «${project.name}»`}
          title="Настройки проекта"
        >
          <Settings size={17} strokeWidth={1.5} aria-hidden="true" />
        </Link>
      </header>

      <span className={styles.badge}>
        <span
          className={styles.dot}
          data-color={statusColor}
          aria-hidden="true"
        />
        {statusLabel}
      </span>

      <div className={styles.members}>
        <div className={styles.avatars} aria-hidden="true">
          {project.members.slice(0, 3).map((member, index) => (
            <span
              key={member.id}
              className={styles.avatar}
              data-color={index}
            >
              {getInitials(member.name || member.email)}
            </span>
          ))}
        </div>

        <span>Участников: {project.members.length}</span>
      </div>

      {error ? (
        <div className={styles.errorBlock}>
          <p className={styles.error} role="alert">
            {error}
          </p>

          <button
            className={styles.retryButton}
            type="button"
            onClick={retry}
          >
            Повторить загрузку
          </button>
        </div>
      ) : data ? (
        <>
          <div className={styles.sources}>
            <p className={styles.source}>
              <span
                className={styles.dot}
                data-color={gitlabColor}
                aria-hidden="true"
              />

              <span>
                GitLab ·{' '}
                {sourceText(project.gitlab_url, gitlabDays, 'gitlab')}
              </span>
            </p>

            <p className={styles.source}>
              <span
                className={styles.dot}
                data-color={redmineColor}
                aria-hidden="true"
              />

              <span>
                Redmine ·{' '}
                {sourceText(project.redmine_url, redmineDays, 'redmine')}
              </span>
            </p>
          </div>

          <footer className={styles.footer}>
            <div className={styles.progressHeading}>
              <span className={styles.deadline}>
                {project.deadline
                  ? `Сроки: до ${formatDate(project.deadline)}`
                  : 'Сроки не указаны'}
              </span>

              <span
                className={styles.percentage}
                title="Прогресс за последние 30 дней"
              >
                {data.summary.progress_percent === null
                  ? '—'
                  : `${data.summary.progress_percent}%`}
              </span>
            </div>

            {data.summary.progress_percent === null ? (
              <div
                className={styles.emptyProgress}
                role="img"
                aria-label="Прогресс: нет данных"
              />
            ) : (
              <progress
                className={styles.progress}
                max={100}
                value={data.summary.progress_percent}
                aria-label={`Прогресс проекта «${project.name}» за последние 30 дней`}
              />
            )}
          </footer>
        </>
      ) : null}
    </article>
  )
}