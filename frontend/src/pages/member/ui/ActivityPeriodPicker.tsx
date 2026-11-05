import { useId, useState } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from '@/shared/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/shared/ui/popover'

interface ActivityPeriodPickerProps {
  value: string
  onChange: (value: string) => void
}

const months = [
  'Янв', 'Фев', 'Мар', 'Апр',
  'Май', 'Июн', 'Июл', 'Авг',
  'Сен', 'Окт', 'Ноя', 'Дек',
]

function selectedYear(value: string): number | null {
  if (!/^\d{4}-\d{2}$/.test(value)) return null

  const year = Number(value.slice(0, 4))
  const month = Number(value.slice(5, 7))

  return month >= 1 && month <= 12 ? year : null
}

function periodLabel(value: string): string {
  if (value === 'all') return 'Весь период'

  if (selectedYear(value) === null) return 'Выберите месяц'

  const date = new Date(`${value}-01T00:00:00`)

  const label = new Intl.DateTimeFormat('ru-RU', {
    month: 'long',
    year: 'numeric',
  })
    .format(date)
    .replace(/\s*г\.$/, '')
    .trim()

  return label.charAt(0).toUpperCase() + label.slice(1)
}

export function ActivityPeriodPicker({
  value,
  onChange,
}: ActivityPeriodPickerProps) {
  const yearId = useId()
  const [open, setOpen] = useState(false)

  const [year, setYear] = useState(
    () => selectedYear(value) ?? new Date().getFullYear(),
  )

  function select(value: string) {
    onChange(value)
    setOpen(false)
  }

  return (
    <Popover
      open={open}
      onOpenChange={(nextOpen) => {
        if (nextOpen) {
          const currentYear = selectedYear(value)

          if (currentYear !== null) {
            setYear(currentYear)
          }
        }

        setOpen(nextOpen)
      }}
    >
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className="h-9 min-w-[172px] justify-between gap-4 rounded-lg bg-white text-xs font-normal"
          aria-label={`Период карты активности: ${periodLabel(value)}`}
        >
          {periodLabel(value)}
          <ChevronDown size={15} aria-hidden="true" />
        </Button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={6}
        className="w-[268px] rounded-xl border-[#cbd4ce] bg-white p-3 text-[#18201c] shadow-xl"
      >
        <div className="mb-3 flex items-center justify-between">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-8 rounded-lg"
            disabled={year <= 1900}
            onClick={() => setYear((current) => current - 1)}
            aria-label="Предыдущий год"
          >
            <ChevronLeft size={15} aria-hidden="true" />
          </Button>

          <strong
            id={yearId}
            className="text-sm"
            aria-live="polite"
          >
            {year}
          </strong>

          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-8 rounded-lg"
            disabled={year >= 9999}
            onClick={() => setYear((current) => current + 1)}
            aria-label="Следующий год"
          >
            <ChevronRight size={15} aria-hidden="true" />
          </Button>
        </div>

        <div
          className="grid grid-cols-3 gap-2"
          role="group"
          aria-labelledby={yearId}
        >
          {months.map((month, index) => {
            const monthValue =
              `${year}-${String(index + 1).padStart(2, '0')}`

            const selected = value === monthValue

            return (
              <Button
                key={month}
                type="button"
                variant="outline"
                aria-pressed={selected}
                className="h-9 rounded-lg text-xs"
                style={{
                    backgroundColor: selected ? '#e6f7eb' : '#ffffff',
                    borderColor: selected ? '#22bf45' : '#e1e7e3',
                    color: '#18201c',
                    fontWeight: selected ? 600 : 400,
                }}
                onClick={() => select(monthValue)}
              >
                {month}
              </Button>
            )
          })}
        </div>

        <div className="mt-3 border-0 border-t border-solid border-[#e5eae7] pt-2">
          <Button
            type="button"
            variant="ghost"
            aria-pressed={value === 'all'}
            className="h-9 w-full justify-between px-1 text-xs font-normal"
            onClick={() => select('all')}
          >
            Весь период

            <span
              aria-hidden="true"
              className={[
                'flex size-4 items-center justify-center rounded border border-solid text-[11px]',
                value === 'all'
                  ? 'border-[#22bf45] bg-[#e6f7eb] text-[#16852f]'
                  : 'border-[#a6afaa] bg-white',
              ].join(' ')}
            >
              {value === 'all' ? '✓' : ''}
            </span>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}