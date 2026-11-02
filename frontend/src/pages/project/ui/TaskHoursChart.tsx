import type {
  DashboardTask,
} from '../../../entities/project/api/getProjectDashboard'

import styles from './TaskHoursChart.module.css'

interface TaskHoursChartProps {
  tasks: DashboardTask[]
  redmineAvailable: boolean
}

const formatter = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 2,
})

function hours(value: number | null): string {
  return value === null
    ? 'не указан'
    : `${formatter.format(value)} ч`
}

export function TaskHoursChart({
  tasks,
  redmineAvailable,
}: TaskHoursChartProps) {
  const maximum = tasks.reduce(
    (result, task) =>
      Math.max(
        result,
        task.estimated_hours ?? 0,
        task.spent_hours,
      ),
    1,
  )

  const scaleMaximum = Math.ceil(maximum)

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <div>
          <h2>Трудозатраты по задачам</h2>
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

      {!redmineAvailable ? (
        <p className={styles.empty}>
          Подключите Redmine, чтобы видеть трудозатраты.
        </p>
      ) : tasks.length === 0 ? (
        <p className={styles.empty}>
          В выбранном периоде нет задач.
        </p>
      ) : (
        <div className={styles.chart}>
          <div className={styles.axis} aria-hidden="true">
            <span>{formatter.format(scaleMaximum)} ч</span>
            <span>{formatter.format(scaleMaximum / 2)} ч</span>
            <span>0 ч</span>
          </div>

          <div
            className={styles.scroll}
            tabIndex={0}
            role="region"
            aria-label="График трудозатрат. Прокрутите, чтобы увидеть остальные задачи."
          >
            <div className={styles.columns}>
              {tasks.map((task) => (
                <div
                  className={styles.task}
                  key={task.id}
                  tabIndex={0}
                  aria-label={
                    `Задача ${task.id}: ${task.title}. ` +
                    `План: ${hours(task.estimated_hours)}. ` +
                    `Факт за период: ${hours(task.spent_hours)}. ` +
                    `Статус: ${task.status}.`
                  }
                >
                  <div className={styles.tooltip} role="tooltip">
                    <strong>
                      #{task.id} {task.title}
                    </strong>
                    <span>Статус: {task.status}</span>
                    <span>План: {hours(task.estimated_hours)}</span>
                    <span>
                      Факт за период: {hours(task.spent_hours)}
                    </span>
                  </div>

                  <div className={styles.plot} aria-hidden="true">
                    <div className={styles.bars}>
                      {task.estimated_hours === null ? (
                        <span className={styles.noPlan}>—</span>
                      ) : (
                        <span
                          className={styles.planBar}
                          style={{
                            height: `${
                              Math.max(0, task.estimated_hours) /
                              scaleMaximum * 100
                            }%`,
                          }}
                        />
                      )}

                      <span
                        className={styles.actualBar}
                        style={{
                          height: `${
                            Math.max(0, task.spent_hours) /
                            scaleMaximum * 100
                          }%`,
                        }}
                      />
                    </div>
                  </div>

                  <span className={styles.taskId}>#{task.id}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}