import type {
  ProjectPlanningQuality,
} from '../../../entities/project/api/getProjectDashboard'

import styles from './PlanningQualityCard.module.css'

interface PlanningQualityCardProps {
  data: ProjectPlanningQuality | undefined
  redmineAvailable: boolean
  periodLabel: string
}

const categories = [
  { key: 'normal', label: 'Норма', color: '#79d88c' },
  { key: 'warning', label: 'Внимание', color: '#ffd166' },
  { key: 'error', label: 'Ошибка планирования', color: '#ff9daf' },
  { key: 'unplanned', label: 'Без оценки', color: '#dfe5e1' },
] as const

const formatter = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 1,
})

function percent(value: number | null): string {
  return value === null ? '—' : `${formatter.format(value)}%`
}

export function PlanningQualityCard({
  data,
  redmineAvailable,
  periodLabel,
}: PlanningQualityCardProps) {
  if (!redmineAvailable || !data) {
    return (
      <section className={styles.panel}>
        <h2>Качество планирования</h2>

        <p className={styles.note}>
          {!redmineAvailable
            ? 'Подключите Redmine, чтобы видеть показатели.'
            : 'Backend не вернул показатели качества планирования.'}
        </p>
      </section>
    )
  }

  // Геометрия диаграммы строится по количествам.
  // Это позволяет избежать щелей из-за округления процентов.
  let position = 0

  const stops = categories.map((category) => {
    const start = position

    position += data.total > 0
      ? (data.counts[category.key] / data.total) * 100
      : 0

    return `${category.color} ${start}% ${position}%`
  })

  const background = data.total > 0
    ? `conic-gradient(${stops.join(', ')})`
    : '#edf0ee'

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <div>
          <h2>Качество планирования</h2>
          <p className={styles.note}>За выбранный период</p>
        </div>

        <span className={styles.period}>{periodLabel}</span>
      </header>

      <div className={styles.chart}>
        <div
          className={styles.ring}
          style={{ background }}
          aria-hidden="true"
        >
          <div className={styles.center}>
            <strong>
              {data.total > 0
                ? percent(data.percentages.normal)
                : '—'}
            </strong>

            <span>
              {data.total > 0 ? 'задач в норме' : 'нет задач'}
            </span>
          </div>
        </div>
      </div>

      <table className={styles.legend}>
        <caption className={styles.srOnly}>
          Качество планирования: количество и доля задач
        </caption>

        <thead className={styles.srOnly}>
          <tr>
            <th scope="col">Категория</th>
            <th scope="col">Количество задач</th>
            <th scope="col">Доля</th>
          </tr>
        </thead>

        <tbody>
          {categories.map((category) => (
            <tr key={category.key}>
              <th scope="row">
                <span
                  className={styles.dot}
                  style={{ backgroundColor: category.color }}
                  aria-hidden="true"
                />
                {category.label}
              </th>

              <td>{data.counts[category.key]}</td>
              <td>{percent(data.percentages[category.key])}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className={styles.explanation}>
        Норма — превышение оценки до 10%, внимание — до 20%,
        ошибка — более 20%. Учитываются и незавершённые задачи.
      </p>
    </section>
  )
}