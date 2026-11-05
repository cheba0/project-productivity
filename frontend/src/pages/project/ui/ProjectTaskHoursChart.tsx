import {useEffect, useState} from 'react'
import {getProjectDashboard, type ProjectDashboard, type ProjectSprint} from '../../../entities/project/api/getProjectDashboard'
import {getProjectSyncStatus} from '../../../entities/project/api/syncProject'
import {useProjectSyncStore} from '../../../store/projectSyncStore'
import {TaskHoursChart} from './TaskHoursChart'

interface ProjectTaskHoursChartProps {
  projectId: string
  sprints: ProjectSprint[]
  today: string
  selectedPeriod: string
  onSelectSprint: (number: number) => void
  refreshKey: number
}

interface ChartResult {
  key: string
  data: ProjectDashboard | null
  error: string | null
}

export function ProjectTaskHoursChart({
  projectId, sprints, today, selectedPeriod, onSelectSprint, refreshKey,
}: ProjectTaskHoursChartProps) {
  const revision = useProjectSyncStore((state) => state.revision)
  const [retry, setRetry] = useState(0)
  const [result, setResult] = useState<ChartResult | null>(null)
  const requestKey = JSON.stringify([projectId, revision, refreshKey, retry])
  const current = result?.key === requestKey ? result : null

  useEffect(() => {
    const controller = new AbortController()

    async function load() {
      try {
        const status = await getProjectSyncStatus(projectId, controller.signal)
        if (controller.signal.aborted) return

        if (!status.has_cached_data || !status.period) {
          throw new Error('Данные проекта ещё не загружены. Нажмите «Обновить данные».')
        }

        const data = await getProjectDashboard(projectId, status.period, controller.signal)
        if (controller.signal.aborted) return

        setResult({key: requestKey, data, error: null})
      } catch (reason: unknown) {
        if (controller.signal.aborted) return

        setResult({
          key: requestKey,
          data: null,
          error: reason instanceof Error ? reason.message : 'Не удалось загрузить трудозатраты.',
        })
      }
    }

    void load()
    return () => controller.abort()
  }, [projectId, requestKey])

  if (!current || !current.data) {
    return (
      <section className="min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-5 shadow-sm">
        <h2 className="m-0 text-[15px] font-bold">Трудозатраты по задачам</h2>

        {!current ? (
          <p className="mt-5 text-sm text-[#748079]" role="status">Загружаем задачи за весь период…</p>
        ) : (
          <div className="mt-5 space-y-3 text-sm text-[#748079]" role="alert">
            <p>{current.error}</p>
            <button
              type="button"
              className="cursor-pointer rounded-lg border border-solid border-[#d6ded8] bg-white px-3 py-2 text-xs"
              onClick={() => setRetry((value) => value + 1)}
            >
              Повторить
            </button>
          </div>
        )}
      </section>
    )
  }

  return (
    <TaskHoursChart
      tasks={current.data.tasks}
      sprints={sprints}
      today={today}
      selectedPeriod={selectedPeriod}
      onSelectSprint={onSelectSprint}
      redmineAvailable={current.data.sources.redmine !== 'not_configured'}
    />
  )
}