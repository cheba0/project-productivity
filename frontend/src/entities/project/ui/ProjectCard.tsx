import { Archive, Settings, Users } from 'lucide-react'
import * as Progress from '@radix-ui/react-progress'
import { activityLabels, type Project } from '../model/types'
import styles from './ProjectCard.module.css'
import { Link } from 'react-router'

const dateFormatter = new Intl.DateTimeFormat('ru-RU')

function formatDate(value: string): string {
  return dateFormatter.format(new Date(`${value}T00:00:00`))
}

export function ProjectCard({ project }: { project: Project }) {
  const activity = project.activity
  const integration = (id: number | null, days?: number) =>
    id == null
      ? 'не подключён'
      : days == null
        ? `проект #${id}`
        : `${days} дн. назад`

  if (project.category === 'archived') {
    const hasTasks =
      project.tasksCompleted != null &&
      project.tasksTotal != null

    const hasHours =
      project.actualHours != null &&
      project.plannedHours != null

    const progress =
      project.tasksCompleted != null &&
      project.tasksTotal != null &&
      project.tasksTotal > 0
        ? Math.min(
            100,
            Math.max(
              0,
              (project.tasksCompleted / project.tasksTotal) * 100,
            ),
          )
        : project.progress

    return (
      <article className={`${styles.card} ${styles.archivedCard}`}>
        <div className={styles.heading}>
          <h2>{project.name}</h2>
        </div>

        <span className={styles.status}>
          <Archive size={16} aria-hidden="true" />
          В архиве
          {project.archivedAt && (
            <> · с {formatDate(project.archivedAt)}</>
          )}
        </span>

        <div className={styles.members}>
          <Users size={20} aria-hidden="true" />
          {project.members == null
            ? 'Участники: нет данных'
            : `Участников: ${project.members}`}
        </div>

        <p className={styles.archiveDetail}>
          Задачи:{' '}
          {hasTasks
            ? `${project.tasksCompleted} из ${project.tasksTotal}`
            : 'нет данных'}
        </p>

        <p className={styles.archiveDetail}>
          Трудозатраты:{' '}
          {hasHours
            ? `факт ${project.actualHours} / план ${project.plannedHours} ч`
            : 'нет данных'}
        </p>

        <div className={styles.footer}>
          <p>
            Сроки:{' '}
            {project.startedAt && project.deadline
              ? `${formatDate(project.startedAt)} – ${formatDate(project.deadline)}`
              : 'не указаны'}
          </p>

          {progress == null ? (
            <p className={styles.noProgress}>Прогресс: нет данных</p>
          ) : (
            <Progress.Root
              className={styles.track}
              value={progress}
              aria-label={`Прогресс проекта ${project.name}`}
            >
              <Progress.Indicator
                className={styles.fill}
                style={{
                  transform: `translateX(-${100 - progress}%)`,
                }}
              />
            </Progress.Root>
          )}
        </div>
      </article>
    )
  }

  return (
    <article className={styles.card}>
      <div className={styles.heading}>
        <h2>{project.name}</h2>
        <Link
          className="icon-button"
          to={`/projects/${encodeURIComponent(project.id)}/settings`}
          state={{ projectName: project.name }}
          aria-label={`Настройки проекта «${project.name}»`}
          title="Настройки проекта"
        >
          <Settings size={20} aria-hidden="true" />
        </Link>
      </div>
      <span className={styles.status}>
        <span className={styles.dot} data-status={activity} />
        {activity ? activityLabels[activity] : 'Статус не указан'}
      </span>
      <div className={styles.members}>
        <Users size={20} aria-hidden="true" />
        {project.members == null
          ? 'Участники: нет данных'
          : `Участников: ${project.members}`}
      </div>
      <p className={styles.integration}>
        <span className={styles.dot} data-status={activity} />
        GitLab · {integration(project.gitlabProjectId, project.gitlabDaysAgo)}
      </p>
      <p className={styles.integration}>
        <span className={styles.dot} data-status={activity} />
        Redmine ·{' '}
        {integration(project.redmineProjectId, project.redmineDaysAgo)}
      </p>
      <div className={styles.footer}>
        <p>
          Срок:{' '}
          {project.deadline
            ? `до ${new Intl.DateTimeFormat('ru-RU').format(new Date(`${project.deadline}T00:00:00`))}`
            : 'не указан'}
        </p>
        {project.progress == null ? (
          <p className={styles.noProgress}>Прогресс: нет данных</p>
        ) : (
          <>
            <Progress.Root
              className={styles.track}
              value={project.progress}
              aria-label={`Прогресс проекта ${project.name}`}
            >
              <Progress.Indicator
                className={styles.fill}
                style={{ transform: `translateX(-${100 - project.progress}%)` }}
              />
            </Progress.Root>
            <span className="sr-only">Выполнено {project.progress}%</span>
          </>
        )}
      </div>
    </article>
  )
}
