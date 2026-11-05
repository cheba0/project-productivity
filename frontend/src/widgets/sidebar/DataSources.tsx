import {useEffect, useState} from 'react'
import {RefreshCw} from 'lucide-react'
import {useLocation} from 'react-router'
import {getProjects} from '../../entities/project'
import {getProjectSyncStatus} from '../../entities/project/api/syncProject'
import {useAuthStore} from '../../store/authStore'
import {useProjectSyncStore} from '../../store/projectSyncStore'

interface DataSourcesProps {
  disabled?: boolean
}

interface SyncSummary {
  key: string
  timestamp: number | null
  message: string
  details: string[]
}

const relativeFormatter = new Intl.RelativeTimeFormat('ru', {numeric: 'always'})
const dateFormatter = new Intl.DateTimeFormat('ru-RU', {dateStyle: 'short', timeStyle: 'short'})

function formatRelativeTime(timestamp: number, now: number): string {
  const seconds = Math.max(0, Math.floor((now - timestamp) / 1000))

  if (seconds < 60) return 'только что'
  if (seconds < 3600) return relativeFormatter.format(-Math.floor(seconds / 60), 'minute')
  if (seconds < 86400) return relativeFormatter.format(-Math.floor(seconds / 3600), 'hour')
  return relativeFormatter.format(-Math.floor(seconds / 86400), 'day')
}

export function DataSources({disabled = false}: DataSourcesProps) {
  const email = useAuthStore((state) => state.user?.email)

  return <DataSourcesContent key={email ?? 'guest'} email={email} disabled={disabled} />
}

function DataSourcesContent({email, disabled}: DataSourcesProps & {email?: string}) {
  const {pathname} = useLocation()
  const syncing = useProjectSyncStore((state) => state.syncing)
  const revision = useProjectSyncStore((state) => state.revision)
  const syncOwnedProjects = useProjectSyncStore((state) => state.syncOwnedProjects)
  const [result, setResult] = useState<SyncSummary | null>(null)
  const [retry, setRetry] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  const requestKey = JSON.stringify([email, pathname, revision, retry])
  const current = result?.key === requestKey ? result : null

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 60_000)
    const refresh = () => {
      setNow(Date.now())
      setRetry((value) => value + 1)
    }

    window.addEventListener('focus', refresh)

    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', refresh)
    }
  }, [])

  useEffect(() => {
    if (!email) return
    const controller = new AbortController()

    async function loadStatus() {
      try {
        const response = await getProjects('active', controller.signal)
        if (controller.signal.aborted) return

        const normalizedEmail = email!.trim().toLowerCase()
        const projects = response.items.filter((project) =>
          project.members.some((member) => member.is_owner && member.email.trim().toLowerCase() === normalizedEmail),
        )

        if (!projects.length) {
          setResult({key: requestKey, timestamp: null, message: 'Нет активных проектов для обновления', details: []})
          return
        }

        const results = await Promise.allSettled(
          projects.map((project) => getProjectSyncStatus(project.id, controller.signal)),
        )

        if (controller.signal.aborted) return

        const timestamps: number[] = []
        const details: string[] = []
        let neverSynced = 0

        results.forEach((item, index) => {
          const name = projects[index].name

          if (item.status === 'rejected') {
            details.push(`${name}: не удалось проверить обновление`)
            return
          }

          const status = item.value
          const timestamp = status.last_success_at ? Date.parse(status.last_success_at) : NaN

          if (status.state === 'ready' && status.has_cached_data && Number.isFinite(timestamp)) {
            timestamps.push(timestamp)
            return
          }

          if (status.state === 'never_synced' || status.state === 'not_configured') neverSynced += 1

          const reason = status.state === 'not_configured' ? 'источники не настроены'
            : status.state === 'never_synced' ? 'данные ещё не загружены'
            : status.state === 'error' ? 'ошибка обновления'
            : 'требуется обновление данных'

          details.push(`${name}: ${reason}`)
        })

        if (timestamps.length === projects.length) {
          setResult({key: requestKey, timestamp: Math.min(...timestamps), message: '', details: []})
          return
        }

        const message = neverSynced === projects.length ? 'Данные ещё не обновлялись' : 'Не все проекты обновлены'
        setResult({key: requestKey, timestamp: null, message, details})
      } catch {
        if (controller.signal.aborted) return
        setResult({key: requestKey, timestamp: null, message: 'Не удалось проверить обновление', details: []})
      }
    }

    void loadStatus()
    return () => controller.abort()
  }, [email, requestKey])

  const timestamp = current?.timestamp
  const message = !email ? 'Войдите для обновления данных'
    : syncing ? 'Обновляем данные…'
    : !current ? 'Проверяем обновление…'
    : timestamp != null ? `Последнее обновление ${formatRelativeTime(timestamp, now)}`
    : current.message

  const title = timestamp != null ? `Последнее обновление: ${dateFormatter.format(timestamp)}` : undefined

  return (
    <section className="mt-5 rounded-[16px] border border-[#e2e7e4] bg-[#fafcfb] p-3" aria-label="Источники данных" aria-busy={syncing}>
      <p className="text-[13px] leading-5 text-[#748079]">Источники данных</p>

      <div className="mt-1 flex items-center justify-between gap-3 text-[14px] font-bold text-[#111813]">
        <span>GitLab</span>
        <span>Redmine</span>
      </div>

      <p className="mt-2 text-[11px] leading-relaxed text-[#748079]" title={title} role="status">
        {message}
      </p>

      <button
        className="mt-2 flex min-h-8 w-full cursor-pointer items-center justify-center gap-2 rounded-full !border-0 bg-[#e7f7ec] px-3 py-1.5 text-[12px] text-[#111813] !shadow-none transition-colors hover:bg-[#d8f0df] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#22c55e] disabled:cursor-not-allowed disabled:opacity-60"
        type="button"
        disabled={disabled || syncing || !email}
        onClick={() => {if (email) void syncOwnedProjects(email)}}
      >
        <RefreshCw className={syncing ? 'animate-spin' : ''} size={16} aria-hidden="true" />
        {syncing ? 'Обновляем…' : 'Обновить данные'}
      </button>

      {!syncing && Boolean(current?.details.length) && (
        <details className="mt-2 text-[11px] leading-relaxed text-[#748079]">
          <summary className="cursor-pointer">Подробности</summary>
          <ul className="mt-1 space-y-1">
            {current?.details.map((detail, index) => <li key={index}>{detail}</li>)}
          </ul>
        </details>
      )}
    </section>
  )
}