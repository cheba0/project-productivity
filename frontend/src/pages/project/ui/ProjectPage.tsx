import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Link, useParams } from 'react-router'

import {
  getProject,
  getProjectDashboard,
  getProjectSprints,
  type ProjectDashboard,
  type ProjectDto,
  type ProjectSprint,
} from '../../../entities/project'

import styles from './ProjectPage.module.css'

function dateOnly(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU').format(
    new Date(value.includes('T') ? value : `${value}T00:00:00`),
  )
}

function activityText(value: string | null, now: number): string {
  if (!value) return 'Нет данных'

  const timestamp = Date.parse(value)
  if (!Number.isFinite(timestamp)) return 'Нет данных'

  const hours = Math.max(
    0,
    Math.floor((now - timestamp) / 3_600_000),
  )

  if (hours < 1) return 'Менее часа назад'
  if (hours < 24) return `${hours} ч назад`

  return `${Math.floor(hours / 24)} дн. назад`
}

function deadlineText(value: string, today: string): string {
  // Сравниваем календарные даты без влияния переходов часового пояса.
  const days = Math.round(
    (Date.parse(`${value}T00:00:00Z`) -
      Date.parse(`${today}T00:00:00Z`)) /
      86_400_000,
  )

  if (days < 0) return `Просрочено на ${Math.abs(days)} дн.`
  if (days === 0) return 'Сегодня'
  if (days === 1) return 'Завтра'

  return `Через ${days} дн.`
}

export function ProjectPage() {
  const { projectId } = useParams()

  return projectId ? (
    <ProjectDashboardPage key={projectId} projectId={projectId} />
  ) : (
    <p role="alert">Не указан идентификатор проекта.</p>
  )
}

function ProjectDashboardPage({
  projectId,
}: {
  projectId: string
}) {
  const [project, setProject] = useState<ProjectDto | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const [sprints, setSprints] = useState<ProjectSprint[]>([])
  const [period, setPeriod] = useState('recent')
  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(Date.now())
    }, 60_000)

    return () => window.clearInterval(timer)
  }, [])
  const [dashboard, setDashboard] =
    useState<ProjectDashboard | null>(null)

  const [projectError, setProjectError] = useState<string | null>(null)
  const [dataError, setDataError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    Promise.all([
      getProject(projectId, controller.signal),
      getProjectSprints(projectId, controller.signal),
    ])
      .then(([projectData, sprintData]) => {
        if (controller.signal.aborted) return

        setSprints(sprintData.items)

        if (sprintData.current_sprint !== null) {
          setPeriod(String(sprintData.current_sprint))
        }

        setProject(projectData)
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

    const end = new Date()
    const start = new Date(end)
    start.setDate(start.getDate() - 29)

    const query =
      period === 'recent'
        ? { start: dateOnly(start), end: dateOnly(end) }
        : { sprint: Number(period) }

    getProjectDashboard(project.id, query, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setDashboard(result)
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setDataError(
            error instanceof Error
              ? error.message
              : 'Не удалось загрузить показатели.',
          )
        }
      })

    return () => controller.abort()
  }, [project, period, reload])

  function changePeriod(value: string) {
    if (value === period) return

    setDashboard(null)
    setDataError(null)
    setPeriod(value)
  }

  function refresh() {
    setDashboard(null)
    setDataError(null)
    setReload((value) => value + 1)
  }

  if (projectError) {
    return (
      <section>
        <Link to="/">← Проекты</Link>
        <p role="alert">{projectError}</p>
      </section>
    )
  }

  if (!project) {
    return <p role="status">Загрузка проекта…</p>
  }

  const sprintIndex = sprints.findIndex(
    (sprint) => String(sprint.number) === period,
  )

  const previousSprint = sprints[sprintIndex - 1]
  const nextSprint =
    sprintIndex >= 0 ? sprints[sprintIndex + 1] : undefined

  const today = dateOnly(new Date(now))

  const openTasks = dashboard?.tasks.filter((task) => !task.done) ?? []

  const overdueCount = openTasks.filter(
    (task) => task.due_date && task.due_date < today,
  ).length

  const upcomingTasks = openTasks
    .filter((task) => task.due_date !== null)
    .sort((a, b) => a.due_date!.localeCompare(b.due_date!))
    .slice(0, 5)

  const summary = dashboard?.summary

  return (
    <section className={styles.page}>
      <div className={styles.toolbar}>
        <nav className={styles.breadcrumbs} aria-label="Навигационная цепочка">
          <Link to="/">Проекты</Link>
          <span aria-hidden="true">›</span>
          <span aria-current="page">{project.name}</span>
        </nav>

        <div className={styles.periodControls}>
          <button
            className={styles.arrowButton}
            type="button"
            disabled={!previousSprint}
            onClick={() => {
              if (previousSprint) {
                changePeriod(String(previousSprint.number))
              }
            }}
            aria-label="Предыдущий спринт"
          >
            <ChevronLeft size={17} aria-hidden="true" />
          </button>

          <select
            className={styles.periodSelect}
            value={period}
            onChange={(event) => changePeriod(event.target.value)}
            aria-label="Период показателей"
          >
            <option value="recent">Последние 30 дней</option>

            {sprints.map((sprint) => (
              <option key={sprint.number} value={sprint.number}>
                Спринт {sprint.number}
              </option>
            ))}
          </select>

          <button
            className={styles.arrowButton}
            type="button"
            disabled={!nextSprint}
            onClick={() => {
              if (nextSprint) {
                changePeriod(String(nextSprint.number))
              }
            }}
            aria-label="Следующий спринт"
          >
            <ChevronRight size={17} aria-hidden="true" />
          </button>
        </div>
      </div>

      <header className={styles.projectHeader}>
        <h1>{project.name}</h1>

        <span className={styles.badge}>
          {project.archived_at
            ? 'В архиве'
            : project.is_paused
              ? 'На паузе'
              : 'Активный проект'}
        </span>

        <p className={styles.dates}>
          <strong>Сроки:</strong>{' '}
          {project.start_date ? formatDate(project.start_date) : '—'}
          {' — '}
          {project.deadline ? formatDate(project.deadline) : '—'}
        </p>

        <Link
          className={styles.settings}
          to={`/projects/${project.id}/settings`}
          state={{ projectName: project.name }}
        >
          Настройки
        </Link>
      </header>

      {dataError ? (
        <div className={styles.errorPanel} role="alert">
          <p>{dataError}</p>
          <button className="button" type="button" onClick={refresh}>
            Повторить
          </button>
        </div>
      ) : !dashboard || !summary ? (
        <p role="status">Загрузка показателей проекта…</p>
      ) : (
        <>
          <p className={styles.periodNote}>
            Период: {formatDate(dashboard.period.start)} —{' '}
            {formatDate(dashboard.period.end)}
          </p>

          <div className={styles.overview}>
            <div className={styles.stats}>
              <article className={styles.stat}>
                <h2>Выполнено</h2>
                <strong>{summary.tasks_done} задач</strong>
                <p>
                  {summary.progress_percent === null
                    ? 'Нет данных о прогрессе'
                    : `${summary.progress_percent}% из ${summary.tasks_total} задач`}
                </p>
              </article>

              <article className={styles.stat}>
                <h2>Незавершённые задачи</h2>
                <strong>{summary.tasks_in_progress} задач</strong>
                <p>Просрочено: {overdueCount}</p>
              </article>

              <article className={styles.stat}>
                <h2>Активность · GitLab</h2>
                <strong>
                  {dashboard.sources.gitlab === 'not_configured'
                    ? 'Не подключён'
                    : activityText(summary.last_gitlab_activity, now)}
                </strong>
                <p>Коммитов за период: {summary.commits}</p>
              </article>

              <article className={styles.stat}>
                <h2>Активность · Redmine</h2>
                <strong>
                  {dashboard.sources.redmine === 'not_configured'
                    ? 'Не подключён'
                    : activityText(summary.last_redmine_activity, now)}
                </strong>
                <p>Фактические трудозатраты: {summary.actual_hours} ч</p>
              </article>
            </div>

            <section className={styles.deadlines}>
              <h2>Ближайшие дедлайны</h2>

              {upcomingTasks.length === 0 ? (
                <p className={styles.empty}>
                  Нет незавершённых задач со сроком в выбранной выборке.
                </p>
              ) : (
                <div className={styles.tableWrapper}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th scope="col">Название задачи</th>
                        <th scope="col">Срок</th>
                      </tr>
                    </thead>

                    <tbody>
                      {upcomingTasks.map((task) => (
                        <tr key={task.id}>
                          <td>
                            #{task.id} {task.title}
                          </td>

                          <td
                            className={
                              task.due_date! < today
                                ? styles.overdue
                                : styles.upcoming
                            }
                            title={formatDate(task.due_date!)}
                          >
                            {deadlineText(task.due_date!, today)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        </>
      )}
    </section>
  )
}