import {useEffect, useState} from 'react'
import {getProjectDashboard, type DashboardTask, type ProjectSprint} from '../../../entities/project/api/getProjectDashboard'
import {getProjectSyncStatus} from '../../../entities/project/api/syncProject'
import {getTaskQuality} from '../../../entities/project/lib/taskQuality'
import {useProjectSyncStore} from '../../../store/projectSyncStore'

interface PlanningQualityCardProps {
  projectId: string
  tasks: DashboardTask[]
  redmineAvailable: boolean
  periodLabel: string
  isSprint: boolean
  previousSprint?: ProjectSprint
}

interface ComparisonResult {
  key: string
  percent: number | null
  error: boolean
}

const categories = [
  {key: 'normal', label: 'Норма', color: '#79d88c'},
  {key: 'warning', label: 'Внимание', color: '#ffd166'},
  {key: 'error', label: 'Ошибка планирования', color: '#ff9daf'},
  {key: 'planned', label: 'Запланировано', color: '#dfe5e1'},
] as const

type Category = (typeof categories)[number]['key']

const formatter = new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 1})

function percent(value: number | null): string {
  return value === null ? '—' : `${formatter.format(value)}%`
}

function calculateQuality(tasks: DashboardTask[]) {
  const counts: Record<Category, number> = {normal: 0, warning: 0, error: 0, planned: 0}

  for (const task of tasks) {
    const category = getTaskQuality(task)
    if (category !== null) counts[category] += 1
  }

  const completed = counts.normal + counts.warning + counts.error

  return {
    counts,
    total: completed + counts.planned,
    normalCompletedPercent: completed > 0 ? (counts.normal / completed) * 100 : null,
  }
}

export function PlanningQualityCard({
  projectId, tasks, redmineAvailable, periodLabel, isSprint, previousSprint,
}: PlanningQualityCardProps) {
  const revision = useProjectSyncStore((state) => state.revision)
  const [comparison, setComparison] = useState<ComparisonResult | null>(null)
  const [retry, setRetry] = useState(0)
  const previousStart = previousSprint?.start
  const previousEnd = previousSprint?.end
  const requestKey = JSON.stringify([projectId, previousStart, previousEnd, revision, retry])
  const currentComparison = comparison?.key === requestKey ? comparison : null
  const quality = calculateQuality(tasks)

  useEffect(() => {
    if (!isSprint || !redmineAvailable || !previousStart || !previousEnd) return

    const controller = new AbortController()
    const start = previousStart
    const end = previousEnd

    async function loadComparison() {
      try {
        const status = await getProjectSyncStatus(projectId, controller.signal)
        if (controller.signal.aborted) return

        const available = status.period

        if (!status.has_cached_data || !available || start < available.start || end > available.end) {
          setComparison({key: requestKey, percent: null, error: false})
          return
        }

        const dashboard = await getProjectDashboard(projectId, {start, end}, controller.signal)
        if (controller.signal.aborted) return

        const previousQuality = dashboard.sources.redmine === 'not_configured'
          ? null
          : calculateQuality(dashboard.tasks).normalCompletedPercent

        setComparison({key: requestKey, percent: previousQuality, error: false})
      } catch {
        if (controller.signal.aborted) return
        setComparison({key: requestKey, percent: null, error: true})
      }
    }

    void loadComparison()
    return () => controller.abort()
  }, [projectId, isSprint, redmineAvailable, previousStart, previousEnd, requestKey])

  if (!redmineAvailable) {
    return (
      <section className="min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-5">
        <h2 className="m-0 text-[15px] font-bold">Качество планирования</h2>
        <p className="mt-3 text-xs text-[#748079]">Подключите Redmine, чтобы видеть показатели.</p>
      </section>
    )
  }

  let position = 0

  const stops = categories.map((category) => {
    const start = position
    position += quality.total > 0 ? (quality.counts[category.key] / quality.total) * 100 : 0
    return `${category.color} ${start}% ${position}%`
  })

  const background = quality.total > 0 ? `conic-gradient(${stops.join(', ')})` : '#edf0ee'
  const currentPercent = quality.normalCompletedPercent
  const previousPercent = currentComparison?.percent ?? null
  const difference = currentPercent !== null && previousPercent !== null
    ? Math.round((currentPercent - previousPercent) * 10) / 10
    : null

  let comparisonContent = <span>Нет данных для сравнения</span>

  if (previousSprint && currentPercent !== null) {
    if (!currentComparison) {
      comparisonContent = <span>Загружаем сравнение…</span>
    } else if (currentComparison.error) {
      comparisonContent = (
        <span>
          Не удалось загрузить сравнение.{' '}
          <button
            className="cursor-pointer border-0 bg-transparent p-0 text-inherit underline underline-offset-2"
            type="button"
            onClick={() => setRetry((value) => value + 1)}
          >
            Повторить
          </button>
        </span>
      )
    } else if (difference !== null) {
      const color = difference > 0 ? 'text-[#169c39]' : difference < 0 ? 'text-[#d95770]' : 'text-[#59665f]'

      comparisonContent = (
        <span>
          <strong className={`${color} text-sm font-bold`}>
            {difference > 0 ? '▲ +' : difference < 0 ? '▼ ' : ''}
            {formatter.format(difference)}% 
          </strong>
          {' '}к спринту {previousSprint.number}
        </span>
      )
    }
  }

  return (
    <section className="min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-5 shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h2 className="m-0 text-base font-bold leading-snug">Качество планирования</h2>
          <p className="mt-1 text-[13px] leading-snug text-[#748079]">
            Нажмите на спринт на графике
          </p>
        </div>

        <span className="shrink-0 rounded-full border border-solid border-[#d6ded8] px-3 py-1.5 text-xs">
          {periodLabel}
        </span>
      </header>

      <div className="flex justify-center py-6">
        <div className="grid size-[196px] place-items-center rounded-full" style={{background}}>
          <div className="flex size-[132px] flex-col items-center justify-center rounded-full bg-white p-3 text-center">
            <strong className="text-[36px] leading-tight text-[#18201c]">
              {percent(currentPercent)}
            </strong>
            <span className="mt-1 text-xs leading-snug text-[#748079]">
              {currentPercent === null ? 'Нет данных о выполненных' : 'выполненных в норме'}
            </span>
          </div>
        </div>
      </div>

      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Количество и доля задач в каждой категории качества</caption>
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
            const share = quality.total > 0 ? (count / quality.total) * 100 : null

            return (
              <tr key={category.key}>
                <th scope="row" className="border-0 border-t border-solid border-[#edf0ee] py-3 text-left font-normal">
                  <span
                    className="mr-2 inline-block size-3 rounded-[3px]"
                    style={{backgroundColor: category.color}}
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

      {isSprint && (
        <div
          className="mt-4 flex min-h-11 items-center rounded-xl bg-[#f4f6f5] px-4 py-3 text-[13px] leading-relaxed text-[#59665f]"
          role="status"
        >
          {comparisonContent}
        </div>
      )}
    </section>
  )
}