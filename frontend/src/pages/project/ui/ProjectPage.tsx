import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { useProjectSyncStore } from '../../../store/projectSyncStore'
import { TaskHoursChart } from './TaskHoursChart'
import { PlanningQualityCard } from './PlanningQualityCard'
import { StudentWorkloadTable } from './StudentWorkloadTable'
import { createPortal } from 'react-dom'
import { useProjectHeaderStore } from '../../../store/projectHeaderStore'

import {
  getProject,
  getProjectDashboard,
  getProjectSprints,
  getProjectSyncStatus,
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

function deadlineText(days: number): string {
  if (days < 0) {
    return `Просрочено на ${Math.abs(days)} дн.`
  }

  if (days === 0) return 'Сегодня'
  if (days === 1) return 'Завтра'

  return `Через ${days} дн.`
}

function projectStatusColor(status: string): string {
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
      return 'gray'
  }
}

function calendarDay(value: string): number {
  return Date.parse(`${value}T00:00:00Z`)
}

function projectTimeline(
  start: string | null,
  end: string | null,
  today: string,
) {
  if (!start || !end) return null

  const first = calendarDay(start)
  const last = calendarDay(end)
  const current = calendarDay(today)

  if (
    !Number.isFinite(first) ||
    !Number.isFinite(last) ||
    !Number.isFinite(current) ||
    last < first
  ) {
    return null
  }

  const daysRemaining = Math.round(
    (last - current) / 86_400_000,
  )

  const percent =
    first === last
      ? current >= last ? 100 : 0
      : Math.min(
          100,
          Math.max(0, ((current - first) / (last - first)) * 100),
        )

  return {
    percent,
    label:
      current < first
        ? `До начала ${Math.round((first - current) / 86_400_000)} дн.`
        : daysRemaining > 0
          ? `Осталось ${daysRemaining} дн.`
          : daysRemaining === 0
            ? 'Срок заканчивается сегодня'
            : `Срок истёк ${Math.abs(daysRemaining)} дн. назад`,
  }
}

function safeExternalUrl(value: string | null): string | null {
  if (!value) return null

  try {
    const url = new URL(value)

    return url.protocol === 'https:' || url.protocol === 'http:'
      ? url.href
      : null
  } catch {
    return null
  }
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
  const syncRevision = useProjectSyncStore((state) => state.revision)
  const [project, setProject] = useState<ProjectDto | null>(null)
  const [periodNotice, setPeriodNotice] = useState<string | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const [sprints, setSprints] = useState<ProjectSprint[]>([])
  const [period, setPeriod] = useState('all')
  const headerControlsElement = useProjectHeaderStore((state) => state.controlsElement)
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

    async function loadDashboard() {
      try {
        const syncStatus = await getProjectSyncStatus(
          projectId,
          controller.signal,
        )

        if (controller.signal.aborted) return

        const available = syncStatus.period

        if (!syncStatus.has_cached_data || !available) {
          throw new Error(
            'Данные проекта ещё не загружены. Нажмите «Обновить данные».',
          )
        }

        let requestedStart = available.start
        let requestedEnd = available.end

        if (period === 'recent') {
          const end = new Date()
          const start = new Date(end)

          start.setDate(start.getDate() - 29)

          requestedStart = dateOnly(start)
          requestedEnd = dateOnly(end)
        } else if (period !== 'all') {
          const selectedSprint = sprints.find(
            (sprint) => String(sprint.number) === period,
          )

          if (!selectedSprint) {
            throw new Error('Выбранный спринт не найден.')
          }

          requestedStart = selectedSprint.start
          requestedEnd = selectedSprint.end
        }

        const start =
          requestedStart < available.start
            ? available.start
            : requestedStart

        const end =
          requestedEnd > available.end
            ? available.end
            : requestedEnd

        if (start > end) {
          throw new Error(
            'За выбранный период нет сохранённых данных.',
          )
        }

        const result = await getProjectDashboard(
          projectId,
          { start, end },
          controller.signal,
        )

        if (controller.signal.aborted) return

        const notices: string[] = []

        if (start !== requestedStart || end !== requestedEnd) {
          notices.push(
            `Данные доступны за часть выбранного периода: ` +
            `${formatDate(start)} — ${formatDate(end)}.`,
          )
        }

        if (syncStatus.last_error) {
          notices.push(
            'Последняя синхронизация завершилась ошибкой. ' +
            'Показаны ранее сохранённые данные.',
          )
        }

        setDashboard(result)
        setDataError(null)
        setPeriodNotice(notices.length ? notices.join(' ') : null)
      } catch (reason: unknown) {
        if (controller.signal.aborted) return

        setDashboard(null)
        setPeriodNotice(null)
        setDataError(
          reason instanceof Error
            ? reason.message
            : 'Не удалось загрузить показатели проекта.',
        )
      }
    }

    void loadDashboard()

    return () => controller.abort()
  }, [project, projectId, period, sprints, reload, syncRevision])

  function changePeriod(value: string) {
    if (value === period) return
    
    setDashboard(null)
    setDataError(null)
    setPeriodNotice(null)
    setPeriod(value)
  }

  function refresh() {
    setDashboard(null)
    setDataError(null)
    setPeriodNotice(null)
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
  const timeline = projectTimeline(
    project.start_date,
    project.deadline,
    today,
  )

  const externalLinks = [
    {
      label: 'GL',
      title: 'Открыть проект в GitLab',
      url: safeExternalUrl(project.gitlab_url),
    },
    {
      label: 'RM',
      title: 'Открыть проект в Redmine',
      url: safeExternalUrl(project.redmine_url),
    },
    {
      label: 'ВП',
      title: 'Открыть витрину проекта',
      url: safeExternalUrl(project.showcase_url),
    },
  ]

  const openTasks = dashboard?.tasks.filter((task) => !task.done) ?? []

  const overdueCount = openTasks.filter(
    (task) => task.due_date && task.due_date < today,
  ).length

  const deadlines = dashboard?.upcoming_deadlines
  const summary = dashboard?.summary

  return (
    <section className={styles.page}>
      {headerControlsElement &&
        createPortal(
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
              <option value="all">Весь доступный период</option>
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
          </div>,
          headerControlsElement,
        )}

      <header className={styles.projectHeader}>
        <div className={styles.projectIdentity}>
          <h1>{project.name}</h1>

          <span className={styles.badge}>
            <span
              className={styles.statusDot}
              data-color={
                project.archived_at
                  ? 'gray'
                  : projectStatusColor(project.status)
              }
              aria-hidden="true"
            />

            {project.archived_at
              ? 'В архиве'
              : project.status_label}
          </span>
        </div>

        <div className={styles.timeline}>
          <p className={styles.dates}>
            <strong>Сроки:</strong>{' '}
            {project.start_date
              ? formatDate(project.start_date)
              : '—'}
            {' — '}
            {project.deadline
              ? formatDate(project.deadline)
              : '—'}
          </p>

          {timeline && (
            <>
              <progress
                className={styles.timelineProgress}
                max={100}
                value={timeline.percent}
                aria-label="Прошедшая часть срока проекта"
              />

              <span className={styles.timelineLabel}>
                {timeline.label}
              </span>
            </>
          )}
        </div>

        <nav
          className={styles.externalLinks}
          aria-label="Ресурсы проекта"
        >
          {externalLinks.map((item) =>
            item.url ? (
              <a
                key={item.label}
                className={styles.externalLink}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={item.title}
                title={item.title}
              >
                {item.label}
              </a>
            ) : (
              <span
                key={item.label}
                className={styles.externalLinkDisabled}
                title={`${item.label}: ссылка не указана`}
                aria-label={`${item.label}: ссылка не указана`}
              >
                {item.label}
              </span>
            ),
          )}
        </nav>
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
          {periodNotice && (
            <p className={styles.notice} role="status">
              {periodNotice}
            </p>
          )}

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
              <h2>Близкие дедлайны</h2>

              {!deadlines ? (
                <p className={styles.empty}>
                  Backend не вернул данные о сроках.
                </p>
              ) : !deadlines.available ? (
                <p className={styles.empty}>
                  {deadlines.reason === 'redmine_not_configured'
                    ? 'Подключите Redmine, чтобы видеть сроки задач.'
                    : deadlines.reason === 'no_due_dates_in_source'
                      ? 'Нет незавершённых задач с указанным сроком.'
                      : 'Данные о сроках пока недоступны.'}
                </p>
              ) : (
                <>
                  {deadlines.items.length === 0 ? (
                    <p className={styles.empty}>
                      Просроченных задач и близких дедлайнов нет.
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
                          {deadlines.items.map((task) => (
                            <tr key={task.id}>
                              <td>
                                #{task.id} {task.title || 'Без названия'}
                              </td>

                              <td
                                className={
                                  task.overdue
                                    ? styles.overdue
                                    : styles.upcoming
                                }
                                title={formatDate(task.due_date)}
                              >
                                {deadlineText(task.days_remaining)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {deadlines.total_matching > deadlines.items.length && (
                    <p className={styles.empty}>
                      Показано {deadlines.items.length} из{' '}
                      {deadlines.total_matching} задач.
                    </p>
                  )}
                </>
              )}

              {deadlines && deadlines.open_tasks_without_due_date > 0 && (
                <p className={styles.empty}>
                  Незавершённых задач без срока:{' '}
                  {deadlines.open_tasks_without_due_date}.
                </p>
              )}
            </section>
          </div>
          <div className={styles.chartsRow}>
            <TaskHoursChart
              tasks={dashboard.tasks}
              redmineAvailable={
                dashboard.sources.redmine !== 'not_configured'
              }
            />

            <PlanningQualityCard
              data={dashboard.planning_quality}
              redmineAvailable={
                dashboard.sources.redmine !== 'not_configured'
              }
              periodLabel={
                period === 'all'
                  ? 'Весь период'
                  : period === 'recent'
                    ? 'Последние 30 дней'
                    : `Спринт ${period}`
              }
            />
          </div>
          <StudentWorkloadTable
            projectId={projectId} 
            students={dashboard.students}
            gitlabAvailable={
              dashboard.sources.gitlab !== 'not_configured'
            }
            redmineAvailable={
              dashboard.sources.redmine !== 'not_configured'
            }
          />
        </>
      )}
    </section>
  )
}