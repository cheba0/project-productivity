import type {
  ProjectSprintHours,
} from '../../../entities/project/api/getProjectDashboard'

import styles from './SprintHoursChart.module.css'

interface SprintHoursChartProps {
  data: ProjectSprintHours | undefined
}

const numberFormat = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 2,
})

function hours(value: number | null): string {
  return value === null
    ? 'Нет данных'
    : `${numberFormat.format(value)} ч`
}

function date(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`))
}

export function SprintHoursChart({
  data,
}: SprintHoursChartProps) {
  if (!data?.available) {
    const message =
      !data
        ? 'Backend не вернул трудозатраты по спринтам.'
        : data.reason === 'project_start_date_missing'
          ? 'Укажите дату начала проекта, чтобы распределить данные по спринтам.'
          : data.reason === 'redmine_not_configured'
            ? 'Подключите Redmine, чтобы видеть трудозатраты.'
            : 'Трудозатраты по спринтам пока недоступны.'

    return (
      <section className={styles.panel}>
        <h2>Трудозатраты по спринтам</h2>
        <p className={styles.note}>{message}</p>
      </section>
    )
  }

  const maximum = data.items.reduce(
    (current, item) =>
      Math.max(
        current,
        item.planned_hours ?? 0,
        item.actual_hours ?? 0,
      ),
    1,
  )

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <div>
          <h2>Трудозатраты по спринтам</h2>
          <p className={styles.note}>
            За выбранный период. План — по дате начала задачи,
            факт — по дате записи трудозатрат.
          </p>
        </div>

        <div className={styles.legend} aria-label="Легенда">
          <span>
            <i className={styles.planMark} aria-hidden="true" />
            План
          </span>
          <span>
            <i className={styles.actualMark} aria-hidden="true" />
            Факт
          </span>
        </div>
      </header>

      {data.items.length === 0 ? (
        <p className={styles.note}>
          В выбранном периоде нет спринтов проекта.
        </p>
      ) : (
        <div className={styles.list}>
          {data.items.map((item) => (
            <article className={styles.sprint} key={item.sprint}>
              <div className={styles.sprintHeader}>
                <div>
                  <h3>Спринт {item.sprint}</h3>
                  <p className={styles.note}>
                    {date(item.start)} — {date(item.end)}
                  </p>
                </div>

                {item.partial_period && (
                  <span className={styles.partial}>
                    Неполный период
                  </span>
                )}
              </div>

              {item.partial_period && (
                <p className={styles.note}>
                  Учтены данные: {date(item.visible_start)} —{' '}
                  {date(item.visible_end)}.
                </p>
              )}

              <div className={styles.barRow}>
                <span>План</span>

                <div className={styles.track} aria-hidden="true">
                  {item.planned_hours !== null && (
                    <div
                      className={styles.planBar}
                      style={{
                        width: `${Math.max(0, item.planned_hours) / maximum * 100}%`,
                      }}
                    />
                  )}
                </div>

                <strong>{hours(item.planned_hours)}</strong>
              </div>

              <div className={styles.barRow}>
                <span>Факт</span>

                <div className={styles.track} aria-hidden="true">
                  {item.actual_hours !== null && (
                    <div
                      className={styles.actualBar}
                      style={{
                        width: `${Math.max(0, item.actual_hours) / maximum * 100}%`,
                      }}
                    />
                  )}
                </div>

                <strong>{hours(item.actual_hours)}</strong>
              </div>

              <p className={styles.note}>
                Разница факта и плана:{' '}
                {item.deviation_hours === null
                  ? 'нет данных'
                  : `${item.deviation_hours > 0 ? '+' : ''}${hours(item.deviation_hours)}`}
              </p>
            </article>
          ))}
        </div>
      )}

      {(data.unallocated_estimated_tasks ?? 0) > 0 && (
        <p className={styles.warning}>
          Задач с оценкой, но без даты начала:{' '}
          {data.unallocated_estimated_tasks}.
          {' '}Их плановые трудозатраты —{' '}
          {hours(data.unallocated_plan_hours ?? null)}.
          {' '}Backend не распределил их по спринтам.
        </p>
      )}
    </section>
  )
}