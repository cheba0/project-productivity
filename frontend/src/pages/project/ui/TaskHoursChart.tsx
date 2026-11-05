import {useEffect, useState, type MouseEvent} from 'react'
import {createPortal} from 'react-dom'
import type {DashboardTask, ProjectSprint} from '../../../entities/project/api/getProjectDashboard'
import {getTaskQuality} from '../../../entities/project/lib/taskQuality'

interface TaskHoursChartProps {
  tasks: DashboardTask[]
  sprints: ProjectSprint[]
  today: string
  selectedPeriod: string
  onSelectSprint: (number: number) => void
  redmineAvailable: boolean
}

interface SprintGroup {
  key: string
  sprint: ProjectSprint | null
  tasks: DashboardTask[]
}

interface TooltipState {
  task: DashboardTask
  kind: 'plan' | 'fact'
  label: string
  left: number
  top: number
  width: number
}

const TASK_WIDTH = 36
const PLAN_WIDTH = 29
const FACT_WIDTH = 19
const CHART_HEIGHT = 280

const formatter = new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 2})
const dateFormatter = new Intl.DateTimeFormat('ru-RU', {day: 'numeric', month: 'short'})

function hours(value: number | null): string {
  return value === null || !Number.isFinite(value) ? '—' : formatter.format(value)
}

function formatDate(value: string): string {
  return dateFormatter.format(new Date(`${value}T00:00:00`))
}

function validHours(value: number | null): number {
  return value !== null && Number.isFinite(value) ? Math.max(0, value) : 0
}

function taskAppearance(task: DashboardTask, normalColor: string, normalEdge: string) {
  const estimate = task.estimated_hours

  if (estimate === null || !Number.isFinite(estimate) || estimate <= 0 || !Number.isFinite(task.spent_hours)) {
    return {label: 'Нет оценки для сравнения', color: '#a6b2aa', edge: '#66776d'}
  }

  const deviation = (task.spent_hours - estimate) / estimate

  if (deviation <= 0.1 + 1e-9) {
    return {label: 'Факт в пределах нормы', color: normalColor, edge: normalEdge}
  }

  if (deviation <= 0.2 + 1e-9) {
    return {label: 'Превышение до 20%', color: '#ffd166', edge: '#e5a000'}
  }

  return {label: 'Превышение более 20%', color: '#ff9daf', edge: '#ff4265'}
}

function LegendPair({colors, label}: {colors: [string, string]; label: string}) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span className="inline-flex gap-0.5" aria-hidden="true">
        {colors.map((color) => (
          <i key={color} className="block h-3 w-2.5 rounded-[3px]" style={{backgroundColor: color}} />
        ))}
      </span>
      {label}
    </span>
  )
}

export function TaskHoursChart({
  tasks, sprints, today, selectedPeriod, onSelectSprint, redmineAvailable,
}: TaskHoursChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)

  useEffect(() => {
    const hide = () => setTooltip(null)

    window.addEventListener('scroll', hide, true)
    window.addEventListener('resize', hide)
    window.addEventListener('blur', hide)

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') hide()
    }

    window.addEventListener('keydown', onKeyDown)

    return () => {
      window.removeEventListener('scroll', hide, true)
      window.removeEventListener('resize', hide)
      window.removeEventListener('blur', hide)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [])

  function showTooltip(event: MouseEvent<HTMLSpanElement>, task: DashboardTask, kind: 'plan' | 'fact', label: string) {
    const card = event.currentTarget.closest('[data-sprint-card]')
    if (!card) return

    const rect = card.getBoundingClientRect()
    const width = Math.min(260, window.innerWidth - 24)
    const center = rect.left + rect.width / 2
    const left = Math.max(12, Math.min(center - width / 2, window.innerWidth - width - 12))

    setTooltip({
      task,
      kind,
      label,
      left,
      width,
      top: Math.max(12, Math.min(rect.top + 12, window.innerHeight - 170)),
    })
  }

  const sortedSprints = [...sprints].sort((a, b) => a.number - b.number)
  const tasksBySprint = new Map<number, DashboardTask[]>()
  const unassignedTasks: DashboardTask[] = []

  for (const task of tasks) {
    const start = task.start_date
    const sprint = start ? sortedSprints.find((item) => start >= item.start && start <= item.end) : undefined

    if (!sprint) {
      unassignedTasks.push(task)
      continue
    }

    const items = tasksBySprint.get(sprint.number) ?? []
    items.push(task)
    tasksBySprint.set(sprint.number, items)
  }

  const groups: SprintGroup[] = sortedSprints.map((sprint) => ({
    key: String(sprint.number),
    sprint,
    tasks: tasksBySprint.get(sprint.number) ?? [],
  }))

  if (unassignedTasks.length > 0) {
    groups.push({key: 'unassigned', sprint: null, tasks: unassignedTasks})
  }

  const completed = tasks.filter((task) => task.done).length
  const actual = tasks.reduce((sum, task) => sum + validHours(task.spent_hours), 0)
  const planned = tasks.reduce((sum, task) => sum + validHours(task.estimated_hours), 0)
  const hasEstimates = tasks.some((task) => task.estimated_hours !== null && Number.isFinite(task.estimated_hours))

  const largest = tasks.reduce(
    (value, task) => Math.max(value, validHours(task.estimated_hours), validHours(task.spent_hours)),
    0,
  )

  const maximum = Math.max(5, Math.ceil(largest / 5) * 5)
  const visibleTooltip = tooltip && tasks.includes(tooltip.task) ? tooltip : null

  return (
    <section className="min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-4 shadow-sm sm:p-5">
      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h2 className="m-0 text-[15px] font-bold">Трудозатраты по задачам</h2>

          {redmineAvailable && (
            <p className="mt-1 text-xs leading-relaxed text-[#748079]">
              Выполнено {completed} из {tasks.length} · факт {hours(actual)} ч при плане {hasEstimates ? `${hours(planned)} ч` : '—'}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-[#46524b]" aria-label="Обозначения графика">
          <LegendPair colors={['#c4edce', '#d9d9ff']} label="План" />
          <LegendPair colors={['#79d88c', '#a5a3ff']} label="Норма" />

          <span title="Жёлтый — превышение до 20%, розовый — более 20%">
            <LegendPair colors={['#ff9daf', '#ffd166']} label="Ошибка планирования" />
          </span>

          <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
            <i className="block size-3 rounded-[3px] border border-dashed border-[#a6b2aa]" aria-hidden="true" />
            Запланировано
          </span>
        </div>
      </header>

      {!redmineAvailable ? (
        <p className="mt-5 text-sm text-[#748079]">Подключите Redmine, чтобы видеть трудозатраты.</p>
      ) : groups.length === 0 ? (
        <p className="mt-5 text-sm text-[#748079]">Нет загруженных задач и спринтов.</p>
      ) : (
        <div className="mt-6 flex min-w-0 gap-2">
          <div
            className="mt-[26px] flex w-10 shrink-0 flex-col justify-between text-right text-[11px] text-[#87938c]"
            style={{height: CHART_HEIGHT}}
            aria-hidden="true"
          >
            <span>{hours(maximum)} ч</span>
            <span>{hours(maximum / 2)} ч</span>
            <span>0 ч</span>
          </div>

          <div
            className="min-w-0 flex-1 overflow-x-auto overscroll-x-contain pb-3 focus-visible:outline-2 focus-visible:outline-[#22bf45]"
            tabIndex={0}
            role="region"
            aria-label="Трудозатраты по спринтам с горизонтальной прокруткой"
          >
            <div className="flex w-max min-w-full items-stretch gap-2 px-2 py-3">
              {groups.map((group) => {
                const sprint = group.sprint
                const selected = sprint !== null && selectedPeriod === String(sprint.number)
                const purple = sprint !== null && sprint.number % 2 === 0
                const background = sprint === null ? '#f2f4f3' : purple ? '#eeefff' : '#e8f7ed'
                const planColor = purple ? '#d9d9ff' : '#c4edce'
                const normalColor = purple ? '#a5a3ff' : '#79d88c'
                const normalEdge = purple ? '#7165f5' : '#22b947'

                const normalTasks = group.tasks.filter((task) => getTaskQuality(task) === 'normal').length
                const evaluatedTasks = group.tasks.filter((task) => {
                  const quality = getTaskQuality(task)
                  return quality !== null && quality !== 'planned'
                }).length

                const future = sprint !== null && sprint.start > today
                const ongoing = sprint !== null && sprint.start <= today && sprint.end >= today

                const caption = future
                  ? 'запланирован'
                  : group.tasks.length === 0
                    ? 'нет загруженных задач'
                    : `в норме ${normalTasks} из ${evaluatedTasks}${ongoing ? ' · идёт' : ''}`

                return (
                  <div
                    key={group.key}
                    data-sprint-card
                    className={`relative flex min-w-[156px] shrink-0 flex-col rounded-2xl border-2 border-solid transition-[border-color,box-shadow] duration-200 ${
                        selected ? 'border-[#22bf45] shadow-[0_2px_8px_rgba(34,191,69,0.12)]' : 'border-transparent'
                      } ${
                        sprint ? 'hover:border-[#22bf45] hover:shadow-[0_3px_12px_rgba(34,191,69,0.22)]' : ''
                      }`}
                    style={{backgroundColor: background}}
                  >
                    <div className="flex justify-center px-2 pt-3">
                      {group.tasks.length === 0 ? (
                        <div
                          className="flex w-[136px] items-center justify-center px-3 text-center text-xs text-[#748079]"
                          style={{height: CHART_HEIGHT + 24}}
                        >
                          Нет загруженных задач
                        </div>
                      ) : group.tasks.map((task) => {
                        const appearance = taskAppearance(task, normalColor, normalEdge)
                        const plannedTask = task.start_date === null || task.start_date > today
                        const estimateHeight = validHours(task.estimated_hours) / maximum * 100
                        const actualHeight = validHours(task.spent_hours) / maximum * 100
                        const factHovered = visibleTooltip?.task.id === task.id

                        const description = [
                          `#${task.id} ${task.title}`,
                          `Статус: ${task.status}`,
                          `План: ${hours(task.estimated_hours)} ч`,
                          `Факт: ${hours(task.spent_hours)} ч`,
                          appearance.label,
                        ].join('. ')

                        return (
                          <div
                            key={task.id}
                            className="relative shrink-0"
                            style={{width: TASK_WIDTH}}
                            role="img"
                            aria-label={description}
                          >
                            <div
                              className="relative border-0 border-y border-dashed border-[#cbdace]"
                              style={{height: CHART_HEIGHT}}
                              aria-hidden="true"
                            >
                              <div className="absolute inset-x-0 top-1/2 border-0 border-t border-dashed border-[#cbdace]" />

                              <div className="relative mx-auto h-full" style={{width: PLAN_WIDTH}}>
                                {task.estimated_hours === null ? (
                                  <span className="absolute inset-x-0 bottom-1 text-center text-xs text-[#87938c]">—</span>
                                ) : estimateHeight > 0 ? (
                                  <span
                                    onMouseEnter={(event) => showTooltip(event, task, 'plan', appearance.label)}
                                    onMouseLeave={() => setTooltip(null)}
                                    onClick={(event) => event.stopPropagation()}
                                    className={`absolute inset-x-0 bottom-0 z-10 cursor-default rounded-t-md transition-shadow duration-150 ${plannedTask ? 'border border-dashed border-[#a6b2aa]' : ''}`}
                                    style={{
                                      height: `${estimateHeight}%`,
                                      backgroundColor: plannedTask ? 'transparent' : planColor,
                                    }}
                                  />
                                ) : null}

                                {actualHeight > 0 && (
                                  <span
                                    onMouseEnter={(event) => showTooltip(event, task, 'fact', appearance.label)}
                                    onMouseLeave={() => setTooltip(null)}
                                    onClick={(event) => event.stopPropagation()}
                                    className="absolute bottom-0 left-1/2 z-20 block -translate-x-1/2 cursor-default rounded-t-[5px] transition-shadow duration-150"
                                    style={{
                                      width: FACT_WIDTH,
                                      height: `${actualHeight}%`,
                                      backgroundColor: appearance.color,
                                      boxShadow: factHovered ? `inset 0 0 0 1.5px ${appearance.edge}` : 'none',
                                    }}
                                  />
                                )}
                              </div>
                            </div>

                            <span className="block pt-1.5 text-center text-[11px] text-[#748079]" aria-hidden="true">
                              {task.id}
                            </span>
                          </div>
                        )
                      })}
                    </div>

                    {sprint ? (
                      <button
                        type="button"
                        aria-pressed={selected}
                        aria-label={selected ? `Снять выбор спринта ${sprint.number}` : `Выбрать спринт ${sprint.number}`}
                        onClick={() => {
                          setTooltip(null)
                          onSelectSprint(sprint.number)
                        }}
                        className="mt-auto flex w-full cursor-pointer flex-col items-center gap-1 rounded-b-xl border-0 bg-transparent px-3 py-3 text-[#18201c] shadow-none after:absolute after:inset-0 after:rounded-2xl after:content-[''] focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:outline-offset-[-2px] focus-visible:after:outline-[#22bf45]"
                      >
                        <strong className="text-sm">Спринт {sprint.number}</strong>
                        <span className="text-xs">{formatDate(sprint.start)} — {formatDate(sprint.end)}</span>
                        <span className="text-[11px] text-[#748079]">{caption}</span>
                      </button>
                    ) : (
                      <div className="mt-auto px-3 py-3 text-center text-xs">Без спринта</div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {visibleTooltip && createPortal(
        <div
          role="tooltip"
          className="pointer-events-none fixed z-[10000] rounded-xl bg-[#7774ff] p-3 text-xs leading-relaxed text-white shadow-xl"
          style={{
            left: visibleTooltip.left,
            top: visibleTooltip.top,
            width: visibleTooltip.width,
            maxHeight: 'calc(100dvh - 24px)',
            overflow: 'hidden',
          }}
        >
          <strong className="block break-words">#{visibleTooltip.task.id} {visibleTooltip.task.title}</strong>
          <span className="mt-1 block">{visibleTooltip.task.status}</span>
          <span className="block">
            Факт {hours(visibleTooltip.task.spent_hours)} ч · План {hours(visibleTooltip.task.estimated_hours)} ч
          </span>
          <span className="block">{visibleTooltip.label}</span>
        </div>,
        document.body,
      )}
    </section>
  )
}