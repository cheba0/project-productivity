import {useEffect, useState} from 'react'

import {getProject, getProjectSprints, type ProjectDto} from '../../entities/project'
import type {ProjectSprints} from '../../entities/project/api/getProjectDashboard'
import {useProjectSyncStore} from '../../store/projectSyncStore'

import styles from './CurrentSprint.module.css'

interface CurrentSprintProps {
  projectId: string
  refreshKey: string
}

interface SprintResult {
  key: string
  project: ProjectDto | null
  sprints: ProjectSprints | null
  error: string | null
}

const DAY = 86_400_000

function dateOnly(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function dayNumber(value: string): number {
  return Date.parse(`${value}T00:00:00Z`) / DAY
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric', month: 'short',
  }).format(new Date(`${value}T00:00:00`))
}

export function CurrentSprint({projectId, refreshKey}: CurrentSprintProps) {
  const [result, setResult] = useState<SprintResult | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const [retry, setRetry] = useState(0)

  const syncRevision = useProjectSyncStore((state) => state.revision)
  const today = dateOnly(new Date(now))
  const requestKey = JSON.stringify([projectId, refreshKey, syncRevision, today, retry])

  const current = result?.key === requestKey ? result : null

  useEffect(() => {
    const updateTime = () => setNow(Date.now())
    const timer = window.setInterval(updateTime, 60_000)
    window.addEventListener('focus', updateTime)

    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', updateTime)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    Promise.all([
      getProject(projectId, controller.signal),
      getProjectSprints(projectId, controller.signal),
    ])
      .then(([project, sprints]) => {
        if (controller.signal.aborted) return
        setResult({key: requestKey, project, sprints, error: null})
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return

        setResult({
          key: requestKey,
          project: null,
          sprints: null,
          error: reason instanceof Error ? reason.message : 'Не удалось загрузить спринт.',
        })
      })

    return () => controller.abort()
  }, [projectId, requestKey])

  if (!current) {
    return (
      <section className={styles.panel} aria-label="Текущий спринт">
        <p className={styles.caption}>Текущий спринт</p>
        <p className={styles.note} role="status">Загрузка…</p>
      </section>
    )
  }

  if (current.error || !current.project || !current.sprints) {
    return (
      <section className={styles.panel} aria-label="Текущий спринт">
        <p className={styles.caption}>Текущий спринт</p>
        <p className={styles.note} role="alert">{current.error || 'Данные недоступны.'}</p>
        <button className={styles.retry} type="button" onClick={() => setRetry((value) => value + 1)}>
          Повторить
        </button>
      </section>
    )
  }

  const {project, sprints} = current

  if (project.archived_at) {
    return (
      <section className={styles.panel}>
        <p className={styles.caption}>Состояние проекта</p>
        <strong className={styles.title}>В архиве</strong>
      </section>
    )
  }

  if (!project.start_date) {
    return (
      <section className={styles.panel}>
        <p className={styles.caption}>Текущий спринт</p>
        <p className={styles.note}>Укажите дату начала проекта в настройках.</p>
      </section>
    )
  }

  const sprint = sprints.items.find((item) => item.number === sprints.current_sprint)

  if (!sprint) {
    const beforeStart = today < project.start_date
    const afterDeadline = project.deadline !== null && today > project.deadline

    return (
      <section className={styles.panel}>
        <p className={styles.caption}>Текущий спринт</p>
        <strong className={styles.title}>
          {beforeStart ? 'Проект ещё не начался' : afterDeadline ? 'Срок проекта завершён' : 'Нет текущего спринта'}
        </strong>
        {beforeStart && <p className={styles.note}>Начало: {formatDate(project.start_date)}</p>}
      </section>
    )
  }

  const firstDay = dayNumber(sprint.start)
  const lastDay = dayNumber(sprint.end)
  const currentDay = dayNumber(today)
  const duration = lastDay - firstDay + 1

  // Календарный прогресс на начало сегодняшнего дня.
  const progress = Math.min(100, Math.max(0, (currentDay - firstDay) / duration * 100))
  const remaining = Math.max(0, lastDay - currentDay)

  const sprintNote = remaining === 0
    ? 'Последний день спринта'
    : `До последнего дня спринта: ${remaining} дн.`

  const projectRemaining = project.deadline
    ? dayNumber(project.deadline) - currentDay
    : null

  const projectNote = projectRemaining === null
    ? null
    : projectRemaining > 0
      ? `До срока проекта: ${projectRemaining} дн.`
      : projectRemaining === 0
        ? 'Срок проекта — сегодня'
        : 'Срок проекта прошёл'

  return (
    <section className={styles.panel} aria-label={`Текущий спринт ${sprint.number}`}>
      <p className={styles.caption}>Текущий спринт</p>

      <strong className={styles.title}>
        Спринт {sprint.number} · {formatDate(sprint.start)} — {formatDate(sprint.end)}
      </strong>

      <progress
        className={styles.progress} max={100} value={progress}
        aria-label="Прошедшая часть календарного срока спринта"
      />

      <p className={styles.note}>
        {sprintNote}
        {projectNote && <><br />{projectNote}</>}
      </p>
    </section>
  )
}