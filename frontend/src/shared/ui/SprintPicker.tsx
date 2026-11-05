import {useState} from 'react'
import {Check, ChevronDown, ChevronLeft, ChevronRight} from 'lucide-react'
import {Popover, PopoverContent, PopoverTrigger} from './popover'

interface SprintOption {
  number: number
  start: string
  end: string
}

interface SprintPickerProps {
  value: string
  sprints: SprintOption[]
  onChange: (value: string) => void
}

const dateFormatter = new Intl.DateTimeFormat('ru-RU', {day: 'numeric', month: 'short'})

function formatDate(value: string): string {
  return dateFormatter.format(new Date(`${value}T00:00:00`))
}

const arrowClass = 'flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-lg border border-solid border-[#d6ded8] bg-white text-[#59665f] shadow-none transition-colors hover:bg-[#edf8f0] disabled:cursor-not-allowed disabled:opacity-35 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#22bf45]'

export function SprintPicker({value, sprints, onChange}: SprintPickerProps) {
  const [open, setOpen] = useState(false)
  const items = [...sprints].sort((a, b) => a.number - b.number)
  const index = items.findIndex((item) => String(item.number) === value)
  const selected = items[index]
  const previous = index > 0 ? items[index - 1] : undefined
  const next = index >= 0 ? items[index + 1] : items[0]
  const label = selected ? `Спринт ${selected.number}` : 'Весь период'

  function select(nextValue: string) {
    onChange(nextValue === value ? 'all' : nextValue)
    setOpen(false)
  }

  return (
    <div className="flex min-w-0 max-w-full items-center gap-1.5">
      <button
        className={arrowClass}
        type="button"
        disabled={!selected}
        aria-label={previous ? 'Предыдущий спринт' : 'Показать весь период'}
        onClick={() => onChange(previous ? String(previous.number) : 'all')}
      >
        <ChevronLeft size={16} aria-hidden="true" />
      </button>

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label={`Период показателей: ${label}`}
            className="flex h-9 min-w-0 w-[180px] cursor-pointer items-center justify-between gap-3 rounded-lg border border-solid border-[#d6ded8] bg-white px-3 text-xs text-[#18201c] shadow-none transition-colors hover:border-[#22bf45] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#22bf45]"
          >
            <span className="truncate">{label}</span>
            <ChevronDown size={15} className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
          </button>
        </PopoverTrigger>

        <PopoverContent
          align="end"
          sideOffset={8}
          aria-label="Выбор периода"
          className="w-[280px] max-w-[calc(100vw-24px)] rounded-xl border border-solid border-[#dce5df] bg-white p-2 text-[#18201c] shadow-lg"
        >
          <button
            type="button"
            aria-pressed={value === 'all'}
            onClick={() => select('all')}
            className={`flex w-full cursor-pointer items-center justify-between rounded-lg border-0 px-3 py-2.5 text-left text-xs shadow-none hover:bg-[#edf8f0] focus-visible:outline-2 focus-visible:outline-[#22bf45] ${value === 'all' ? 'bg-[#e7f7ec] font-semibold text-[#16852f]' : 'bg-transparent text-[#18201c]'}`}
          >
            Весь период
            {value === 'all' && <Check size={16} aria-hidden="true" />}
          </button>

          <div className="my-2 border-0 border-t border-solid border-[#edf0ee]" />

          <div className="max-h-[min(320px,50dvh)] space-y-1 overflow-y-auto overscroll-contain">
            {items.map((sprint) => {
              const active = value === String(sprint.number)

              return (
                <button
                  key={sprint.number}
                  type="button"
                  aria-pressed={active}
                  onClick={() => select(String(sprint.number))}
                  className={`flex w-full cursor-pointer items-center justify-between gap-3 rounded-lg border-0 px-3 py-2.5 text-left shadow-none hover:bg-[#edf8f0] focus-visible:outline-2 focus-visible:outline-[#22bf45] ${active ? 'bg-[#e7f7ec] text-[#16852f]' : 'bg-transparent text-[#18201c]'}`}
                >
                  <span className="grid gap-1">
                    <span className="text-xs font-semibold">Спринт {sprint.number}</span>
                    <span className="text-[11px] font-normal text-[#748079]">
                      {formatDate(sprint.start)} — {formatDate(sprint.end)}
                    </span>
                  </span>

                  {active && <Check size={16} className="shrink-0" aria-hidden="true" />}
                </button>
              )
            })}

            {!items.length && <p className="px-3 py-2 text-xs text-[#748079]">Спринты ещё не настроены</p>}
          </div>
        </PopoverContent>
      </Popover>
      
      <button
        className={arrowClass}
        type="button"
        disabled={!next}
        aria-label={selected ? 'Следующий спринт' : 'Первый спринт'}
        onClick={() => {if (next) onChange(String(next.number))}}
      >
        <ChevronRight size={16} aria-hidden="true" />
      </button>
    </div>
  )
}