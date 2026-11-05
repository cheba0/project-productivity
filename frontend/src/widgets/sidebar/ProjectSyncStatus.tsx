import {useEffect, useState} from 'react'
import {getProjectSyncStatus, type ProjectSyncStatus as SyncStatus} from '../../entities/project/api/syncProject'
import {useProjectSyncStore} from '../../store/projectSyncStore'

interface ProjectSyncStatusProps {
  projectId: string
  refreshKey?: string
}

interface StatusResult {
  key: string
  data: SyncStatus | null
  error: string | null
}

const dateFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Дата неизвестна' : dateFormatter.format(date)
}

function getStatusLabel(data: SyncStatus): string {
  switch (data.state) {
    case 'not_configured':
      return 'Источники не настроены'
    case 'never_synced':
      return 'Данные ещё не загружены'
    case 'needs_refresh':
      return 'Требуется обновление данных'
    case 'error':
      return data.has_cached_data ? 'Ошибка обновления · доступны сохранённые данные' : 'Не удалось загрузить данные'
    case 'ready':
      return 'Данные загружены'
  }
}

export function ProjectSyncStatus({projectId, refreshKey = ''}: ProjectSyncStatusProps) {
  const revision = useProjectSyncStore((state) => state.revision)
  const [retry, setRetry] = useState(0)
  const [result, setResult] = useState<StatusResult | null>(null)
  const requestKey = JSON.stringify([projectId, refreshKey, revision, retry])
  const current = result?.key === requestKey ? result : null

  useEffect(() => {
    const controller = new AbortController()

    async function loadStatus() {
      try {
        const data = await getProjectSyncStatus(projectId, controller.signal)
        if (!controller.signal.aborted) setResult({key: requestKey, data, error: null})
      } catch (error) {
        if (controller.signal.aborted) return
        const message = error instanceof Error ? error.message : 'Не удалось проверить обновление'
        setResult({key: requestKey, data: null, error: message})
      }
    }

    void loadStatus()
    return () => controller.abort()
  }, [projectId, requestKey])

  useEffect(() => {
    const refresh = () => setRetry((value) => value + 1)
    window.addEventListener('focus', refresh)
    return () => window.removeEventListener('focus', refresh)
  }, [])

  if (!current) {
    return <p className="mt-2 text-[11px] leading-relaxed text-[#748079]" role="status">Проверяем обновление…</p>
  }

  if (!current.data) {
    return (
      <div className="mt-2 text-[11px] leading-relaxed">
        <p className="text-[#b45309]" title={current.error ?? undefined}>Не удалось проверить обновление</p>
        <button className="mt-1 cursor-pointer text-[#59665f] underline underline-offset-2" type="button" onClick={() => setRetry((value) => value + 1)}>
          Повторить
        </button>
      </div>
    )
  }

  const data = current.data
  const color = data.state === 'ready' ? 'bg-[#22c55e]' : data.state === 'error' ? 'bg-[#fb7185]' : 'bg-[#fbbf24]'

  return (
    <div className="mt-2 space-y-1 text-[11px] leading-relaxed text-[#748079]" role="status">
      {data.last_success_at && (
        <p>
          Последнее обновление:{' '}
          <time dateTime={data.last_success_at}>{formatDate(data.last_success_at)}</time>
        </p>
      )}

      <p className="flex items-start gap-1.5">
        <span className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${color}`} aria-hidden="true" />
        <span>{getStatusLabel(data)}</span>
      </p>
    </div>
  )
}