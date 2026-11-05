import type {
  MemberDashboard,
} from '../../../entities/project/api/getMemberDashboard'
import type {
  ProjectSprint,
} from '../../../entities/project/api/getProjectDashboard'

interface MemberActivityMapProps {
  data: MemberDashboard
  selection: string
  currentSprint: ProjectSprint | null
}

type ActivityDay = MemberDashboard['daily_activity'][number]

interface Cell {
  start: string
  end: string
  days: ActivityDay[]
  expectedDays: number
  weekend: boolean
}

interface Column {
  key: string
  label: string
  year: string
  cells: (Cell | null)[]
}

const numberFormat = new Intl.NumberFormat('ru-RU', {
  maximumFractionDigits: 2,
})

function parseDay(value: string): Date {
  return new Date(`${value}T00:00:00Z`)
}

function key(value: Date): string {
  return value.toISOString().slice(0, 10)
}

function shift(value: string, count: number): string {
  const date = parseDay(value)
  date.setUTCDate(date.getUTCDate() + count)
  return key(date)
}

function monday(value: string): string {
  const date = parseDay(value)
  return shift(value, -((date.getUTCDay() + 6) % 7))
}

function monthEnd(value: string): string {
  const date = parseDay(`${value}-01`)
  date.setUTCMonth(date.getUTCMonth() + 1)
  date.setUTCDate(0)
  return key(date)
}

function formatDay(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(parseDay(value))
}

function monthLabel(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', {
    month: 'short',
    timeZone: 'UTC',
  }).format(parseDay(`${value}-01`))
}

function makeCell(
  start: string,
  end: string,
  byDate: Map<string, ActivityDay>,
  weekend = false,
): Cell {
  const days: ActivityDay[] = []
  let expectedDays = 0

  for (let date = start; date <= end; date = shift(date, 1)) {
    expectedDays += 1
    const row = byDate.get(date)
    if (row) days.push(row)
  }

  return { start, end, days, expectedDays, weekend }
}

function buildMonth(
  month: string,
  byDate: Map<string, ActivityDay>,
): Column[] {
  const first = `${month}-01`
  const last = monthEnd(month)
  const columns: Column[] = []

  for (
    let week = monday(first);
    week <= last;
    week = shift(week, 7)
  ) {
    const cells: (Cell | null)[] = []

    for (let index = 0; index < 7; index += 1) {
      const date = shift(week, index)

      cells.push(
        date < first || date > last
          ? null
          : makeCell(date, date, byDate, index >= 5),
      )
    }

    columns.push({
      key: week,
      label: '',
      year: '',
      cells,
    })
  }

  return columns
}

function buildHistory(
  start: string,
  end: string,
  byDate: Map<string, ActivityDay>,
): Column[] {
  const columns: Column[] = []
  const cursor = parseDay(`${start.slice(0, 7)}-01`)

  while (key(cursor).slice(0, 7) <= end.slice(0, 7)) {
    const month = key(cursor).slice(0, 7)
    const first = `${month}-01`
    const last = monthEnd(month)
    const cells: Cell[] = []

    // Календарные недели, обрезанные границами месяца.
    // Дни соседнего месяца в эту колонку не включаются.
    for (
      let week = monday(first);
      week <= last;
      week = shift(week, 7)
    ) {
      const cellStart = week < first ? first : week
      const weekEnd = shift(week, 6)
      const cellEnd = weekEnd > last ? last : weekEnd

      cells.push(makeCell(cellStart, cellEnd, byDate))
    }

    columns.push({
      key: month,
      label: monthLabel(month),
      year: month.slice(0, 4),
      cells,
    })

    cursor.setUTCMonth(cursor.getUTCMonth() + 1)
  }

  return columns
}

function totals(cell: Cell) {
  return cell.days.reduce(
    (result, day) => ({
      commits: result.commits + day.gitlab_commits,
      entries: result.entries + (day.redmine_updates ?? 0),
      hours: result.hours + (day.redmine_hours ?? 0),
    }),
    { commits: 0, entries: 0, hours: 0 },
  )
}

function intensity(
  value: number,
  maximum: number,
  colors: string[],
): string | null {
  if (value <= 0) return null

  const ratio = value / maximum
  return colors[ratio > 0.66 ? 2 : ratio > 0.33 ? 1 : 0]
}

export function MemberActivityMap({
  data,
  selection,
  currentSprint,
}: MemberActivityMapProps) {
  const monthly = selection !== 'all'

  const byDate = new Map(
    data.daily_activity.map((row) => [row.date, row]),
  )

  const columns = monthly
    ? buildMonth(selection, byDate)
    : buildHistory(data.period.start, data.period.end, byDate)

  const rowCount = monthly
    ? 7
    : Math.max(1, ...columns.map((column) => column.cells.length))

  const cells = columns.flatMap((column) =>
    column.cells.filter((cell): cell is Cell => cell !== null),
  )

  const maxCommits = Math.max(
    1,
    ...cells.map((cell) => totals(cell).commits),
  )

  const maxEntries = Math.max(
    1,
    ...cells.map((cell) => totals(cell).entries),
  )

  const gitlabAvailable =
    data.sources.gitlab !== 'not_configured'

  const redmineAvailable =
    data.sources.redmine !== 'not_configured' &&
    data.profile.redmine_user_id !== null

  const cellSize = monthly ? 52 : 38

  const rowsStyle = {
    gridTemplateRows: `20px 20px repeat(${rowCount}, ${cellSize}px)`,
  }

  function renderCell(cell: Cell | null, index: number) {
    if (!cell) {
      return <span key={index} aria-hidden="true" />
    }

    const values = totals(cell)
    const hasData = cell.days.length > 0
    const partial = hasData && cell.days.length < cell.expectedDays
    const inCurrentSprint = currentSprint !== null && cell.start <= currentSprint.end && cell.end >= currentSprint.start

    const gitlab = gitlabAvailable
      ? intensity(
          values.commits,
          maxCommits,
          ['#d4d2ff', '#aaa7ff', '#7774ff'],
        )
      : null

    const redmine = redmineAvailable
      ? intensity(
          values.entries,
          maxEntries,
          ['#beeac8', '#7bd78f', '#32bf55'],
        )
      : null

    const background = !hasData
      ? '#ffffff'
      : gitlab && redmine
        ? `linear-gradient(135deg, ${gitlab} 50%, ${redmine} 50%)`
        : gitlab || redmine || '#edf0ee'

    const dates = cell.start === cell.end
      ? formatDay(cell.start)
      : `${formatDay(cell.start)} — ${formatDay(cell.end)}`

    const description = [
      dates,
      inCurrentSprint
        ? `Текущий спринт ${currentSprint.number}`
        : '',
      !hasData
        ? 'Нет сохранённых данных'
        : [
            gitlabAvailable
              ? `GitLab: ${values.commits} коммитов`
              : 'GitLab не подключён',
            redmineAvailable
              ? `Redmine: ${values.entries} записей трудозатрат, ${numberFormat.format(values.hours)} ч`
              : 'Нет персональных данных Redmine',
            partial ? 'Данные только за часть недели' : '',
          ].filter(Boolean).join('. '),
    ].filter(Boolean).join('. ')

    return (
      <span
        key={index}
        tabIndex={0}
        role="img"
        aria-label={description}
        title={description}
        className={['block rounded-lg border', 'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#18201c]', inCurrentSprint ? 'ring-1 ring-[#7774ff] ring-offset-2 ring-offset-white' : '',].join(' ')}
        style={{
          width: cellSize,
          height: cellSize,
          background,
          borderStyle:
            !hasData || cell.weekend ? 'dashed' : 'solid',
          borderColor: hasData ? '#bdc8c0' : '#dce0dd',
        }}
      />
    )
  }

  return (
    <div className="flex min-h-[460px] min-w-0 flex-col">
      <div className="grid min-w-0 gap-6 min-[1400px]:grid-cols-[minmax(0,1fr)_130px]">
        <div
          className="min-w-0 overflow-x-auto pb-4 focus-visible:outline-2 focus-visible:outline-[#22bf45]"
          tabIndex={0}
          role="region"
          aria-label={
            monthly
              ? 'Активность по дням месяца'
              : 'Активность по неделям внутри месяцев'
          }
        >
          <div className="flex w-max gap-1.5">
            <div
              className="mr-2 grid gap-1.5 text-[11px] text-[#748079]"
              style={rowsStyle}
            >
              <span />
              <span />

              {Array.from({ length: rowCount }, (_, index) => (
                <span key={index} className="flex items-center">
                  {monthly
                    ? ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][index]
                    : `${index + 1} нед.`}
                </span>
              ))}
            </div>

            {columns.map((column, index) => (
              <div
                key={column.key}
                className="grid gap-1.5"
                style={rowsStyle}
              >
                <span className="text-center text-[11px] text-[#748079]">
                  {!monthly &&
                  (index === 0 || columns[index - 1].year !== column.year)
                    ? column.year
                    : ''}
                </span>

                <span className="text-center text-[11px] text-[#748079]">
                  {monthly
                    ? index === 0 ? monthLabel(selection) : ''
                    : column.label}
                </span>

                {Array.from({ length: rowCount }, (_, cellIndex) =>
                  renderCell(column.cells[cellIndex] ?? null, cellIndex),
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex min-w-0 flex-wrap gap-5 min-[1400px]:flex-col min-[1400px]:border-0 min-[1400px]:border-l min-[1400px]:border-solid min-[1400px]:border-[#edf0ee] min-[1400px]:pl-5">
          <div>
            <strong className="block text-3xl">
              {gitlabAvailable ? data.summary.commits : '—'}
            </strong>
            <span className="text-xs text-[#748079]">коммитов</span>
          </div>

          <div>
            <strong className="block text-3xl">
              {redmineAvailable
                ? data.summary.redmine_entries ?? '—'
                : '—'}
            </strong>
            <span className="text-xs text-[#748079]">
              записей трудозатрат
            </span>
          </div>

          <div>
            <strong className="block text-3xl">
              {gitlabAvailable || redmineAvailable
                ? data.summary.active_weeks
                : '—'}
            </strong>
            <span className="text-xs text-[#748079]">
              активных недель
            </span>
          </div>
        </div>
      </div>

      <footer className="mt-auto flex flex-wrap gap-x-4 gap-y-2 border-0 border-t border-solid border-[#edf0ee] pt-4 text-[11px] text-[#748079]">
        <span className="inline-flex items-center gap-1.5">
          <i
            className="size-4 rounded bg-[#edf0ee]"
            aria-hidden="true"
          />
          Нет активности
        </span>

        <span className="inline-flex items-center gap-1.5">
          GitLab
          {['#d4d2ff', '#aaa7ff', '#7774ff'].map((color) => (
            <i
              key={color}
              className="size-4 rounded"
              style={{ background: color }}
              aria-hidden="true"
            />
          ))}
        </span>

        <span className="inline-flex items-center gap-1.5">
          Redmine
          {['#beeac8', '#7bd78f', '#32bf55'].map((color) => (
            <i
              key={color}
              className="size-4 rounded"
              style={{ background: color }}
              aria-hidden="true"
            />
          ))}
        </span>

        <span className="inline-flex items-center gap-1.5">
          <i
            className="size-4 rounded"
            style={{
              background:
                'linear-gradient(135deg, #7774ff 50%, #32bf55 50%)',
            }}
            aria-hidden="true"
          />
          GitLab + Redmine
        </span>

        <span className="inline-flex items-center gap-1.5">
          <i
            className="size-4 rounded border border-dashed border-[#bdc8c0] bg-[#edf0ee]"
            aria-hidden="true"
          />
          Выходной
        </span>

        <span className="inline-flex items-center gap-1.5">
          <i
            className="size-4 rounded border border-dashed border-[#dce0dd] bg-white"
            aria-hidden="true"
          />
          Нет сохранённых данных
        </span>

        {currentSprint && (
          <span className="inline-flex items-center gap-1.5">
            <i
              className="size-4 rounded border border-solid border-[#7774ff] bg-white"
              aria-hidden="true"
            />
            Текущий спринт {currentSprint.number}
          </span>
        )}
      </footer>
    </div>
  )
}