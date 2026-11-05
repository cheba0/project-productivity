import { useEffect, useState } from 'react'
import { ActivityPeriodPicker } from './ActivityPeriodPicker'
import { Button } from '@/shared/ui/button'
import {getProjectSprints,type ProjectSprint,} from '../../../entities/project/api/getProjectDashboard'

import {
  getMemberDashboard,
  type MemberDashboard,
} from '../../../entities/project/api/getMemberDashboard'
import {
  getProjectSyncStatus,
} from '../../../entities/project/api/syncProject'
import { useProjectSyncStore } from '../../../store/projectSyncStore'

import { MemberActivityMap } from './MemberActivityMap'

interface MemberActivityPanelProps {
  projectId: string
  memberId: string
  selection: string
  onSelectionChange: (value: string) => void
  profileRevision: number
}

function monthRange(value: string) {
  if (!/^\d{4}-\d{2}$/.test(value)) {
    throw new Error('Выберите месяц.')
  }

  const [year, month] = value.split('-').map(Number)

  if (month < 1 || month > 12) {
    throw new Error('Некорректный месяц.')
  }

  const lastDay = new Date(
    Date.UTC(year, month, 0),
  ).getUTCDate()

  return {
    start: `${value}-01`,
    end: `${value}-${String(lastDay).padStart(2, '0')}`,
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU').format(
    new Date(`${value}T00:00:00`),
  )
}

export function MemberActivityPanel({
  projectId,
  memberId,
  selection,
  onSelectionChange,
  profileRevision,
}: MemberActivityPanelProps) {
  const [result, setResult] = useState<{
    key: string
    data: MemberDashboard | null
    currentSprint: ProjectSprint | null
    error: string | null
    notice: string | null
  } | null>(null)

  const [retry, setRetry] = useState(0)

  const syncRevision = useProjectSyncStore(
    (state) => state.revision,
  )

  const requestKey = JSON.stringify([
    projectId,
    memberId,
    selection,
    profileRevision,
    syncRevision,
    retry,
  ])

  useEffect(() => {
    const controller = new AbortController()

    async function loadActivity() {
      try {
        const [sync, sprintData] = await Promise.all([
          getProjectSyncStatus(projectId, controller.signal),
          getProjectSprints(projectId, controller.signal),
        ])

        if (controller.signal.aborted) return
        const currentSprint =
          sprintData.items.find(
            (sprint) => sprint.number === sprintData.current_sprint,
          ) ?? null

        if (!sync.has_cached_data || !sync.period) {
          throw new Error(
            'История ещё не загружена. Нажмите «Обновить данные».',
          )
        }

        const requested =
          selection === 'all'
            ? sync.period
            : monthRange(selection)

        const start =
          requested.start < sync.period.start
            ? sync.period.start
            : requested.start

        const end =
          requested.end > sync.period.end
            ? sync.period.end
            : requested.end

        if (start > end) {
          throw new Error(
            'За этот месяц нет сохранённых данных.',
          )
        }

        const data = await getMemberDashboard(
          projectId,
          memberId,
          { start, end },
          controller.signal,
        )

        if (controller.signal.aborted) return

        const notices: string[] = []

        if (start !== requested.start || end !== requested.end) {
          notices.push(
            `Учтены доступные даты: ${formatDate(start)} — ${formatDate(end)}.`,
          )
        }

        if (sync.last_error) {
          notices.push(
            'Последняя синхронизация завершилась ошибкой. ' +
            'Используется сохранённая история.',
          )
        }

        setResult({
          key: requestKey,
          data,
          currentSprint,
          error: null,
          notice: notices.length ? notices.join(' ') : null,
        })
      } catch (reason: unknown) {
        if (controller.signal.aborted) return

        setResult({
          key: requestKey,
          data: null,
          currentSprint: null,
          error:
            reason instanceof Error
              ? reason.message
              : 'Не удалось загрузить карту активности.',
          notice: null,
        })
      }
    }

    void loadActivity()

    return () => controller.abort()
  }, [
    projectId,
    memberId,
    selection,
    profileRevision,
    syncRevision,
    retry,
    requestKey,
  ])

  const current =
    result?.key === requestKey ? result : null

  return (
    <section className="flex min-w-0 flex-col gap-4 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="m-0 text-sm font-bold">
          Карта активности · GitLab и Redmine
        </h2>

        <ActivityPeriodPicker
          value={selection}
          onChange={onSelectionChange}
        />
      </header>

      {!current ? (
        <p role="status" className="py-6 text-sm text-[#748079]">
          Загружаем историю активности…
        </p>
      ) : current.error ? (
        <div role="alert" className="grid justify-items-start gap-3 py-4">
          <p className="text-sm text-[#748079]">
            {current.error}
          </p>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setRetry((value) => value + 1)}
          >
            Повторить
          </Button>
        </div>
      ) : current.data ? (
        <>
          {current.notice && (
            <p className="text-xs text-[#748079]">
              {current.notice}
            </p>
          )}

          <MemberActivityMap
            data={current.data}
            selection={selection}
            currentSprint={current.currentSprint}
          />
        </>
      ) : null}
    </section>
  )
}