import { Link } from 'react-router'
import { Settings } from 'lucide-react'

import { type ProjectDto } from '../../../entities/project'

import styles from './ProjectDataCard.module.css'

interface ProjectDataCardProps {
  project: ProjectDto
}

function statusColor(status: string): string {
  switch (status) {
    case 'working':
      return 'green'
    case 'partial':
      return 'yellow'
    case 'delayed':
      return 'orange'
    case 'idle':
      return 'red'
    default:
      return 'unknown'
  }
}

function sourceColor(
  url: string | null,
  days: number | null,
  project: ProjectDto,
): string {
  if (!url || days === null) return 'unknown'
  if (days <= project.active_after_days) return 'green'
  if (days <= project.delayed_after_days) return 'yellow'
  return 'red'
}

function sourceText(
  url: string | null,
  days: number | null,
): string {
  if (!url) return 'Не подключён'
  if (days === null) return 'Нет данных об активности'
  if (days === 0) return 'Сегодня'

  return `${days} дн. назад`
}

function formatDate(value: string): string {
  const date = new Date(
    value.includes('T') ? value : `${value}T00:00:00`,
  )

  return new Intl.DateTimeFormat('ru-RU').format(date)
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
  const archived = Boolean(project.archived_at)
  const progress = project.progress_percent

  const sources = [
    {
      name: 'GitLab',
      url: project.gitlab_url,
      days: project.gitlab_inactive_days,
    },
    {
      name: 'Redmine',
      url: project.redmine_url,
      days: project.redmine_inactive_days,
    },
  ]

  const dates =
    project.start_date && project.deadline
      ? `${formatDate(project.start_date)} — ${formatDate(project.deadline)}`
      : project.deadline
        ? `до ${formatDate(project.deadline)}`
        : project.start_date
          ? `с ${formatDate(project.start_date)}`
          : 'не указаны'

  return (
    <article
      className={
        archived
          ? `${styles.card} ${styles.archivedCard}`
          : styles.card
      }
    >
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
          state={{projectName: project.name}}
          aria-label={`Настройки проекта «${project.name}»`}
          title="Настройки проекта"
        >
          <Settings size={17} strokeWidth={1.5} aria-hidden="true" />
        </Link>
      </header>

      <span className={styles.badge}>
        {project.archived_at ? (
          <>В архиве с {formatDate(project.archived_at)}</>
        ) : (
          <>
            <span
              className={styles.dot}
              data-color={statusColor(project.status)}
              aria-hidden="true"
            />
            {project.status_label}
          </>
        )}
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

      {archived ? (
        <div className={styles.archiveDetails}>
          <p>
            Задачи: {project.tasks_done ?? '—'} из{' '}
            {project.tasks_total ?? '—'}
          </p>

          <p>Сроки: {dates}</p>
        </div>
      ) : (
        <div className={styles.sources}>
          {sources.map((source) => (
            <p className={styles.source} key={source.name}>
              <span
                className={styles.dot}
                data-color={sourceColor(
                  source.url,
                  source.days,
                  project,
                )}
                aria-hidden="true"
              />

              <span>
                {source.name} ·{' '}
                {sourceText(source.url, source.days)}
              </span>
            </p>
          ))}
        </div>
      )}

      <footer className={styles.footer}>
        <div className={styles.progressHeading}>
          <span className={styles.deadline}>
            {archived
              ? 'Прогресс'
              : project.deadline
                ? `Сроки: до ${formatDate(project.deadline)}`
                : 'Сроки не указаны'}
          </span>

          <span className={styles.percentage}>
            {progress === null ? '—' : `${progress}%`}
          </span>
        </div>

        {progress === null ? (
          <div
            className={styles.emptyProgress}
            role="img"
            aria-label="Прогресс: нет данных"
          />
        ) : (
          <progress
            className={styles.progress}
            max={100}
            value={progress}
            aria-label={`Прогресс проекта «${project.name}»`}
          />
        )}
      </footer>
    </article>
  )
}