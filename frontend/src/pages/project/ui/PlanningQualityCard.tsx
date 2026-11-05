import type {DashboardTask,} from '../../../entities/project/api/getProjectDashboard'
import {getTaskQuality,} from '../../../entities/project/lib/taskQuality'
interface PlanningQualityCardProps {tasks: DashboardTask[]
  redmineAvailable: boolean
  periodLabel: string
}

const categories = [
  { key: 'normal', label: 'Норма', color: '#79d88c' },
  { key: 'warning', label: 'Внимание', color: '#ffd166' },
  { key: 'error', label: 'Ошибка планирования', color: '#ff9daf' },
  { key: 'planned', label: 'Запланировано', color: '#dfe5e1' },
] as const

type Category = (typeof categories)[number]['key']

const formatter = new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 1,})

function percent(value: number | null): string {return value === null ? '—' : `${formatter.format(value)}%`}

function calculateQuality(tasks: DashboardTask[]) {
  const counts: Record<Category, number> = {
    normal: 0,
    warning: 0,
    error: 0,
    planned: 0,
  }

  for (const task of tasks) {
    const category = getTaskQuality(task)

    if (category !== null) {
      counts[category] += 1
    }
  }

  const completed = counts.normal + counts.warning + counts.error

  const total = completed + counts.planned

  return {
    counts,
    total,
    normalCompletedPercent:
      completed > 0
        ? (counts.normal / completed) * 100
        : null,
  }
}

export function PlanningQualityCard({
  tasks,
  redmineAvailable,
  periodLabel,
}: PlanningQualityCardProps) {
  if (!redmineAvailable) {
    return (
      <section className="min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-5">
        <h2 className="m-0 text-[15px] font-bold">
          Качество планирования
        </h2>

        <p className="mt-3 text-xs text-[#748079]">
          Подключите Redmine, чтобы видеть показатели.
        </p>
      </section>
    )
  }

  const quality = calculateQuality(tasks)

  let position = 0

  const stops = categories.map((category) => {
    const start = position

    position += quality.total > 0
      ? (quality.counts[category.key] / quality.total) * 100
      : 0

    return `${category.color} ${start}% ${position}%`
  })

  const background = quality.total > 0
    ? `conic-gradient(${stops.join(', ')})`
    : '#edf0ee'

  return (
    <section className="min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-5 shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="m-0 text-[15px] font-bold">
          Качество планирования
        </h2>

        <span className="rounded-full border border-solid border-[#d6ded8] px-2.5 py-1 text-[11px]">
          {periodLabel}
        </span>
      </header>

      <div className="flex justify-center py-6">
        <div
          className="grid size-44 place-items-center rounded-full"
          style={{ background }}
        >
          <div className="flex size-[126px] flex-col items-center justify-center rounded-full bg-white p-3 text-center">
            <strong className="text-[30px] leading-tight text-[#18201c]">
              {percent(quality.normalCompletedPercent)}
            </strong>

            <span className="mt-1 text-[11px] leading-snug text-[#748079]">
              {quality.normalCompletedPercent === null
                ? 'Нет данных о выполненных'
                : 'выполненных в норме'}
            </span>
          </div>
        </div>
      </div>

      <table className="w-full border-collapse text-xs">
        <caption className="sr-only">
          Количество и доля задач в каждой категории качества
        </caption>

        <thead className="sr-only">
          <tr>
            <th scope="col">Категория</th>
            <th scope="col">Количество задач</th>
            <th scope="col">Доля задач диаграммы</th>
          </tr>
        </thead>

        <tbody>
          {categories.map((category) => {
            const count = quality.counts[category.key]

            const share = quality.total > 0
              ? (count / quality.total) * 100
              : null

            return (
              <tr key={category.key}>
                <th
                  scope="row"
                  className="border-0 border-t border-solid border-[#edf0ee] py-3 text-left font-normal"
                >
                  <span
                    className="mr-2 inline-block size-2.5 rounded-[3px]"
                    style={{ backgroundColor: category.color }}
                    aria-hidden="true"
                  />
                  {category.label}
                </th>

                <td className="border-0 border-t border-solid border-[#edf0ee] py-3 pl-3 text-right font-semibold">
                  {count}
                </td>

                <td className="border-0 border-t border-solid border-[#edf0ee] py-3 pl-3 text-right text-[#748079]">
                  {percent(share)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}