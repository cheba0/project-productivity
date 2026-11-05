import type {
  DashboardStudent,
} from '../../../entities/project/api/getProjectDashboard'

import styles from './StudentWorkloadTable.module.css'
import { Link } from 'react-router'

interface StudentWorkloadTableProps {
  students: DashboardStudent[]
  gitlabAvailable: boolean
  redmineAvailable: boolean
  projectId: string
}

const formatter = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 2,
})

function initials(value: string): string {
  return value
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function status(value: string) {
  switch (value) {
    case 'working':
      return { label: 'Активен', color: 'green' }
    case 'partial':
      return { label: 'Частично', color: 'yellow' }
    case 'delayed':
      return { label: 'Замедление', color: 'orange' }
    case 'idle':
      return { label: 'Без активности', color: 'red' }
    default:
      return { label: 'Нет данных', color: 'gray' }
  }
}

function roleLabel(value: string): string {
  switch (value) {
    case 'owner':
      return 'Владелец проекта'
    case 'member':
      return 'Участник'
    case 'student':
      return 'Студент'
    default:
      return value
  }
}

function activity(days: number | null): string {
  if (days === null) return 'Нет данных'
  if (days === 0) return 'Сегодня'
  if (days === 1) return 'Вчера'

  return `${days} дн. назад`
}

function hours(value: number | null): string {
  return value === null ? '—' : formatter.format(value)
}

function deviation(value: number | null): string {
  if (value === null) return '—'

  return `${value > 0 ? '+' : ''}${formatter.format(value)}%`
}

export function StudentWorkloadTable({
  students,
  gitlabAvailable,
  redmineAvailable,
  projectId,
}: StudentWorkloadTableProps) {
  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <h2>Трудозатраты по студентам</h2>
        <p>
          Факт за выбранный период и оценки назначенных задач.
        </p>
      </header>

      {students.length === 0 ? (
        <p className={styles.empty}>
          В проекте пока нет участников.
        </p>
      ) : (
        <div className={styles.scroll}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">Участник</th>
                <th scope="col">Статус</th>
                <th scope="col">Последняя активность</th>
                <th scope="col">Факт / план</th>
                <th scope="col">Отклонение</th>
              </tr>
            </thead>

            <tbody>
              {students.map((student, index) => {
                const currentStatus = status(student.activity_status)

                const actual = redmineAvailable
                  ? student.actual_hours
                  : null

                const planned = redmineAvailable
                  ? student.planned_hours
                  : null

                const difference = redmineAvailable
                  ? student.hours_deviation_percent
                  : null

                const maximum = Math.max(
                  actual ?? 0,
                  planned ?? 0,
                  1,
                )

                return (
                  <tr key={student.member_id} className={styles.memberRow}>
                    <td>
                      <div className={styles.person}>
                        <span
                          className={styles.avatar}
                          data-color={index % 5}
                          aria-hidden="true"
                        >
                          {initials(student.name || student.email)}
                        </span>

                        <div className={styles.personText}>
                          <Link
                            to={`/projects/${projectId}/members/${student.member_id}`}
                            className={styles.memberLink}
                          >
                            {student.name || student.email}
                          </Link>

                          <span>{roleLabel(student.role)}</span>
                        </div>
                      </div>
                    </td>

                    <td>
                      <span className={styles.badge}>
                        <i
                          className={styles.dot}
                          data-color={currentStatus.color}
                          aria-hidden="true"
                        />

                        {currentStatus.label}
                      </span>
                    </td>

                    <td>
                      <div className={styles.activity}>
                        <span>
                          GitLab ·{' '}
                          {gitlabAvailable
                            ? activity(student.gitlab_inactive_days)
                            : 'Не подключён'}
                        </span>

                        <span>
                          Redmine ·{' '}
                          {!redmineAvailable
                            ? 'Не подключён'
                            : student.redmine_user_id === null
                              ? 'Не привязан'
                              : activity(student.redmine_inactive_days)}
                        </span>
                      </div>
                    </td>

                    <td>
                      <div className={styles.hours}>
                        <div
                          className={styles.track}
                          aria-hidden="true"
                        >
                          {actual !== null && (
                            <span
                              className={styles.actual}
                              style={{
                                width: `${Math.max(0, actual) / maximum * 100}%`,
                              }}
                            />
                          )}

                          {planned !== null && (
                            <span
                              className={styles.plan}
                              style={{
                                left: `${Math.max(0, planned) / maximum * 100}%`,
                              }}
                            />
                          )}
                        </div>

                        <strong>
                          {hours(actual)} / {hours(planned)} ч
                        </strong>
                      </div>
                    </td>

                    <td>
                      <span className={styles.deviation}>
                        {deviation(difference)}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}