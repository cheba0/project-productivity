import type {
  DashboardTask,
  ProjectSprint,
} from '../../../entities/project/api/getProjectDashboard'

interface TaskHoursChartProps {
  tasks: DashboardTask[]
  sprints: ProjectSprint[]
  today: string
  selectedPeriod: string
  onSelectSprint: (number: number) => void
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

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: '2-digit',
  }).format(new Date(`${value}T00:00:00`))
}

function taskAppearance(task: DashboardTask) {
  const estimate = task.estimated_hours

  if (
    estimate === null ||
    !Number.isFinite(estimate) ||
    estimate <= 0 ||
    !Number.isFinite(task.spent_hours)
  ) {
    return {
      label: 'Нет оценки для сравнения',
      color: '#a6b2aa',
    }
  }

  const deviation = (task.spent_hours - estimate) / estimate

  if (deviation <= 0.1 + 1e-9) {
    return {
      label: 'Факт в пределах нормы',
      color: '#79d88c',
    }
  }

  if (deviation <= 0.2 + 1e-9) {
    return {
      label: 'Превышение до 20%',
      color: '#ffd166',
    }
  }

  return {
    label: 'Превышение более 20%',
    color: '#ff9daf',
  }
}

export function TaskHoursChart({
  tasks,
  sprints,
  today,
  selectedPeriod,
  onSelectSprint,
  redmineAvailable,
}: TaskHoursChartProps) {
  const sortedSprints = [...sprints].sort(
    (a, b) => a.number - b.number,
  )

  const tasksBySprint = new Map<number, DashboardTask[]>()
  const unassignedTasks: DashboardTask[] = []

  for (const task of tasks) {
    const startDate = task.start_date

    const sprint = startDate
      ? sortedSprints.find(
          (item) =>
            startDate >= item.start &&
            startDate <= item.end,
        )
      : undefined

    if (!sprint) {
      unassignedTasks.push(task)
      continue
    }

    const items = tasksBySprint.get(sprint.number) ?? []
    items.push(task)
    tasksBySprint.set(sprint.number, items)
  }

  const groups: {
    key: string
    sprint: ProjectSprint | null
    tasks: DashboardTask[]
  }[] = sortedSprints
    .filter((sprint) => tasksBySprint.has(sprint.number))
    .map((sprint) => ({
      key: String(sprint.number),
      sprint,
      tasks: tasksBySprint.get(sprint.number)!,
    }))

  if (unassignedTasks.length > 0) {
    groups.push({
      key: 'unassigned',
      sprint: null,
      tasks: unassignedTasks,
    })
  }

  const maximum = Math.ceil(
    tasks.reduce(
      (result, task) =>
        Math.max(
          result,
          task.estimated_hours ?? 0,
          task.spent_hours,
        ),
      1,
    ),
  )

  return (
    <section className="min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-5 shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="m-0 text-[15px] font-bold">
          Трудозатраты по задачам
        </h2>

        <div className="flex flex-wrap gap-x-3 gap-y-2 text-[11px] text-[#58675e]">
          <span className="inline-flex items-center gap-1">
            <i
              className="inline-block size-2.5 rounded-sm bg-[#c4edce]"
              aria-hidden="true"
            />
            План
          </span>

          <span className="inline-flex items-center gap-1">
            <i
              className="inline-block size-2.5 rounded-sm bg-[#79d88c]"
              aria-hidden="true"
            />
            Норма
          </span>

          <span className="inline-flex items-center gap-1">
            <i
              className="inline-block size-2.5 rounded-sm bg-[#ffd166]"
              aria-hidden="true"
            />
            Внимание
          </span>

          <span className="inline-flex items-center gap-1">
            <i
              className="inline-block size-2.5 rounded-sm bg-[#ff9daf]"
              aria-hidden="true"
            />
            Ошибка
          </span>

          <span className="inline-flex items-center gap-1">
            <i
              className="inline-block size-2.5 rounded-sm border border-dashed border-[#a6b2aa]"
              aria-hidden="true"
            />
            Запланировано
          </span>
        </div>
      </header>

      {!redmineAvailable ? (
        <p className="mt-5 text-sm text-[#748079]">
          Подключите Redmine, чтобы видеть трудозатраты.
        </p>
      ) : tasks.length === 0 ? (
        <p className="mt-5 text-sm text-[#748079]">
          В выбранном периоде нет задач.
        </p>
      ) : (
        <div className="mt-4 flex min-w-0 gap-2">
          <div
            className="mt-[125px] flex h-[220px] w-10 shrink-0 flex-col justify-between text-right text-[11px] text-[#87938c]"
            aria-hidden="true"
          >
            <span>{formatter.format(maximum)} ч</span>
            <span>{formatter.format(maximum / 2)} ч</span>
            <span>0 ч</span>
          </div>

          <div
            className="min-w-0 flex-1 overflow-x-auto focus-visible:outline-2 focus-visible:outline-[#22bf45]"
            tabIndex={0}
            role="region"
            aria-label="График задач по спринтам с горизонтальной прокруткой"
          >
            <div className="flex w-max min-w-full items-stretch gap-3 pt-28 pb-3">
              {groups.map((group, groupIndex) => {
                const sprint = group.sprint
                const selected =
                  sprint !== null &&
                  selectedPeriod === String(sprint.number)

                return (
                  <div
                    key={group.key}
                    className={[
                      'shrink-0 rounded-xl border border-solid',
                      selected
                        ? 'border-[#22bf45] shadow-sm'
                        : 'border-transparent',
                      sprint === null
                        ? 'bg-[#f2f4f3]'
                        : groupIndex % 2 === 0
                          ? 'bg-[#e8f7ed]'
                          : 'bg-[#eeefff]',
                    ].join(' ')}
                  >
                    <div className="flex px-2 pt-3">
                      {group.tasks.map((task, index) => {
                        const appearance = taskAppearance(task)
                        const planned = task.start_date === null || task.start_date > today

                        return (
                          <div
                            key={task.id}
                            tabIndex={0}
                            className="group relative w-[88px] shrink-0 rounded-md focus-visible:outline-2 focus-visible:outline-[#22bf45]"
                            aria-label={
                              `Задача ${task.id}: ${task.title}. ` +
                              `План: ${hours(task.estimated_hours)}. ` +
                              `Факт за период: ${hours(task.spent_hours)}. ` +
                              `Статус: ${task.status}. ` +
                              appearance.label
                            }
                          >
                            <div
                              role="tooltip"
                              className={[
                                'absolute bottom-[calc(100%+8px)] z-10 hidden',
                                'max-h-[104px] w-[220px] overflow-y-auto',
                                'rounded-lg bg-[#7774ff] p-2.5 text-[11px] leading-relaxed text-white shadow-lg',
                                'group-hover:block group-focus:block',
                                index === group.tasks.length - 1 &&
                                index > 0
                                  ? 'right-0'
                                  : 'left-0',
                              ].join(' ')}
                            >
                              <strong className="block">
                                #{task.id} {task.title}
                              </strong>
                              <span className="block">
                                {task.status} · {appearance.label}
                              </span>
                              <span className="block">
                                План: {hours(task.estimated_hours)}
                              </span>
                              <span className="block">
                                Факт за период: {hours(task.spent_hours)}
                              </span>
                            </div>

                            <div
                              className="relative h-[220px] border-0 border-y border-solid border-[#dce4de]"
                              aria-hidden="true"
                            >
                              <div className="absolute inset-x-0 top-1/2 border-0 border-t border-dashed border-[#dce4de]" />

                              <div className="relative mx-auto h-full w-14">
                                {task.estimated_hours === null ? (
                                  <span className="absolute inset-x-0 bottom-1 text-center text-xs text-[#87938c]">
                                    —
                                  </span>
                                ) : (
                                  <span
                                    className={[
                                      'absolute inset-x-0 bottom-0 rounded-t-lg',
                                      planned
                                        ? 'border border-dashed border-[#a6b2aa] bg-transparent'
                                        : 'bg-[#c4edce]',
                                    ].join(' ')}
                                    style={{
                                      height: `${
                                        Math.max(0, task.estimated_hours) / maximum * 100
                                      }%`,
                                    }}
                                  />
                                )}

                                <span
                                  className="absolute bottom-0 left-1/2 z-10 block w-9 -translate-x-1/2 rounded-t-md"
                                  style={{
                                    height: `${
                                      Math.max(0, task.spent_hours) / maximum * 100
                                    }%`,
                                    backgroundColor: appearance.color,
                                  }}
                                />
                              </div>
                            </div>

                            <span className="block pt-2 text-center text-[11px] text-[#748079]">
                              #{task.id}
                            </span>
                          </div>
                        )
                      })}
                    </div>

                    {sprint ? (
                      <button
                        type="button"
                        aria-pressed={selected}
                        onClick={() => onSelectSprint(sprint.number)}
                        className="flex w-full flex-col items-center gap-1 rounded-b-xl border-0 bg-transparent px-4 py-3 text-[#18201c] hover:bg-black/5 focus-visible:outline-2 focus-visible:outline-[#22bf45]"
                      >
                        <strong className="text-xs">
                          Спринт {sprint.number}
                        </strong>

                        <span className="text-[11px]">
                          {formatDate(sprint.start)} —{' '}
                          {formatDate(sprint.end)}
                        </span>

                        <span className="text-[11px] text-[#748079]">
                          {selected ? 'Выбран' : 'Показать спринт'}
                        </span>
                      </button>
                    ) : (
                      <div className="px-4 py-3 text-center text-xs">
                        Без спринта
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}