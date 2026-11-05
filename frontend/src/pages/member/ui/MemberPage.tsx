import {useEffect, useState} from 'react'
import {createPortal} from 'react-dom'
import {Link, useParams} from 'react-router'
import {ExternalLink, Pencil} from 'lucide-react'

import {Button} from '@/shared/ui/button'
import {getProject, getProjectSprints, type ProjectSprint} from '../../../entities/project'
import {getMemberDashboard, type MemberDashboard} from '../../../entities/project/api/getMemberDashboard'
import {getProjectSyncStatus} from '../../../entities/project/api/syncProject'
import {useAuthStore} from '../../../store/authStore'
import {useProjectHeaderStore} from '../../../store/projectHeaderStore'
import {useProjectSyncStore} from '../../../store/projectSyncStore'
import {SprintPicker} from '../../../shared/ui/SprintPicker'

import {EditMemberDialog} from './EditMemberDialog'
import {MemberActivityPanel} from './MemberActivityPanel'

const numberFormat = new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 2})
const panelClass = 'min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white shadow-sm'

function number(value: number | null): string {
  return value === null ? '—' : numberFormat.format(value)
}

function activity(days: number | null): string {
  if (days === null) return 'Нет данных'
  if (days === 0) return 'Сегодня'
  if (days === 1) return 'Вчера'
  return `${days} дн. назад`
}

function memberStatus(value: string) {
  switch (value) {
    case 'working': return {label: 'Активен', color: '#22bf45'}
    case 'partial': return {label: 'Частично', color: '#ffb600'}
    case 'delayed': return {label: 'Замедление', color: '#ff873f'}
    case 'idle': return {label: 'Без активности', color: '#ff4265'}
    default: return {label: 'Нет данных', color: '#a6afaa'}
  }
}

function sourceColor(days: number | null, activeDays: number, delayedDays: number): string {
  if (days === null) return '#a6afaa'
  if (days <= activeDays) return '#22bf45'
  if (days <= delayedDays) return '#ffb600'
  return '#ff4265'
}

function roleLabel(role: string): string {
  if (role === 'owner') return 'Владелец проекта'
  if (role === 'member') return 'Участник'
  if (role === 'student') return 'Студент'
  return role
}

function profileUrl(value: string | null): string | null {
  if (!value) return null

  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('ru-RU').format(new Date(`${value}T00:00:00`))
}

export function MemberPage() {
  const {projectId, memberId} = useParams()

  if (!projectId || !memberId) {
    return <p role="alert">Не указан проект или участник.</p>
  }

  return <MemberDetails key={`${projectId}:${memberId}`} projectId={projectId} memberId={memberId} />
}

function MemberDetails({projectId, memberId}: {projectId: string; memberId: string}) {
  const [data, setData] = useState<MemberDashboard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const [editing, setEditing] = useState(false)

  const [projectName, setProjectName] = useState('')
  const [ownerEmail, setOwnerEmail] = useState<string | null>(null)
  const [thresholds, setThresholds] = useState({active: 3, delayed: 7})

  const [period, setPeriod] = useState('all')
  const [sprints, setSprints] = useState<ProjectSprint[]>([])
  const [periodNotice, setPeriodNotice] = useState<string | null>(null)

  const [activitySelection, setActivitySelection] = useState('all')
  const [profileRevision, setProfileRevision] = useState(0)

  const userEmail = useAuthStore((state) => state.user?.email)
  const syncRevision = useProjectSyncStore((state) => state.revision)
  const headerControlsElement = useProjectHeaderStore((state) => state.controlsElement)

  useEffect(() => {
    const controller = new AbortController()

    async function load() {
      try {
        const [sync, project, sprintData] = await Promise.all([
          getProjectSyncStatus(projectId, controller.signal),
          getProject(projectId, controller.signal),
          getProjectSprints(projectId, controller.signal),
        ])

        if (controller.signal.aborted) return

        setProjectName(project.name)
        setOwnerEmail(project.members.find((member) => member.is_owner)?.email ?? null)
        setThresholds({active: project.active_after_days, delayed: project.delayed_after_days})
        setSprints(sprintData.items)

        if (!sync.has_cached_data || !sync.period) {
          throw new Error('Данные ещё не загружены. Нажмите «Обновить данные».')
        }

        const available = sync.period
        let requestedStart = available.start
        let requestedEnd = available.end

        if (period !== 'all') {
          const sprint = sprintData.items.find((item) => String(item.number) === period)

          if (!sprint) throw new Error('Выбранный спринт не найден.')

          requestedStart = sprint.start
          requestedEnd = sprint.end
        }

        const start = requestedStart < available.start ? available.start : requestedStart
        const end = requestedEnd > available.end ? available.end : requestedEnd

        if (start > end) {
          throw new Error('За выбранный период нет сохранённых данных.')
        }

        const result = await getMemberDashboard(projectId, memberId, {start, end}, controller.signal)

        if (controller.signal.aborted) return

        const notices: string[] = []

        if (start !== requestedStart || end !== requestedEnd) {
          notices.push(`Данные доступны за часть периода: ${formatDate(start)} — ${formatDate(end)}.`)
        }

        if (sync.last_error) {
          notices.push('Последняя синхронизация завершилась ошибкой. Показаны сохранённые данные.')
        }

        setData(result)
        setError(null)
        setPeriodNotice(notices.length ? notices.join(' ') : null)
      } catch (reason: unknown) {
        if (controller.signal.aborted) return
        setError(reason instanceof Error ? reason.message : 'Не удалось загрузить участника.')
      }
    }

    void load()
    return () => controller.abort()
  }, [projectId, memberId, period, reload, syncRevision])

  function changePeriod(value: string) {
    if (value === period) return

    setEditing(false)
    setData(null)
    setError(null)
    setPeriodNotice(null)
    setPeriod(value)
  }

  function retry() {
    setError(null)
    setReload((value) => value + 1)
  }
  
  const periodControls = headerControlsElement ? createPortal(
    <SprintPicker value={period} sprints={sprints} onChange={changePeriod} />,
    headerControlsElement,
  ) : null

  if (!data) {
    return (
      <>
        {periodControls}
        {error ? (
          <div role="alert" className="grid justify-items-start gap-3">
            <p>{error}</p>
            <Button type="button" variant="outline" onClick={retry}>Повторить</Button>
            <Link to={`/projects/${projectId}`}>Вернуться к проекту</Link>
          </div>
        ) : (
          <p role="status">Загрузка участника…</p>
        )}
      </>
    )
  }

  const {profile, summary} = data
  const normalizedEmail = userEmail?.trim().toLowerCase()
  const canEdit = Boolean(normalizedEmail && (
    normalizedEmail === profile.email.trim().toLowerCase() ||
    normalizedEmail === ownerEmail?.trim().toLowerCase()
  ))

  const name = profile.name?.trim() || profile.email
  const initials = name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  const status = memberStatus(summary.activity_status)

  const gitlabAvailable = data.sources.gitlab !== 'not_configured'
  const redmineAvailable = data.sources.redmine !== 'not_configured'
  const redmineLinked = redmineAvailable && profile.redmine_user_id !== null

  const gitlabUrl = profileUrl(profile.gitlab_profile_url)
  const redmineUrl = profileUrl(profile.redmine_profile_url)

  const actual = redmineLinked ? summary.actual_hours : null
  const planned = redmineLinked ? summary.planned_hours : null
  const deviation = redmineLinked ? summary.hours_deviation_percent : null
  const deviationText = deviation === null ? '—' : `${deviation > 0 ? '+' : ''}${number(deviation)}%`

  const completion = redmineLinked && summary.tasks_total !== null &&
    summary.tasks_total > 0 && summary.tasks_done !== null
      ? Math.round(summary.tasks_done / summary.tasks_total * 100)
      : null

  const stats = [
    {
      title: 'Выполнено',
      value: redmineLinked ? summary.tasks_done ?? '—' : '—',
      description: !redmineLinked
        ? 'Нужна привязка к Redmine'
        : completion === null
          ? `Всего назначено: ${summary.tasks_total ?? '—'} задач`
          : `${completion}% из ${summary.tasks_total} задач`,
      dot: null,
    },
    {
      title: 'В работе',
      value: redmineLinked ? summary.tasks_in_progress ?? '—' : '—',
      description: 'Новые и незавершённые задачи',
      dot: null,
    },
    {
      title: 'Активность · GitLab',
      value: gitlabAvailable ? activity(summary.gitlab_inactive_days) : 'Не подключён',
      description: gitlabAvailable ? `Коммитов за период: ${summary.commits}` : 'Интеграция не настроена',
      dot: sourceColor(gitlabAvailable ? summary.gitlab_inactive_days : null, thresholds.active, thresholds.delayed),
    },
    {
      title: 'Активность · Redmine',
      value: !redmineAvailable ? 'Не подключён' : !redmineLinked ? 'Не привязан' : activity(summary.redmine_inactive_days),
      description: redmineLinked
        ? `Записей трудозатрат: ${summary.redmine_entries ?? '—'}`
        : 'Нет персональных данных',
      dot: sourceColor(redmineLinked ? summary.redmine_inactive_days : null, thresholds.active, thresholds.delayed),
    },
  ]

  return (
    <section className="grid min-w-0 gap-5 text-[#18201c]">
      {periodControls}

      {periodNotice && (
        <p role="status" className="rounded-lg bg-[#fff5df] p-3 text-xs text-[#815d12]">
          {periodNotice}
        </p>
      )}

      {error && (
        <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-[#b42318]">
          <p>Не удалось обновить показатели: {error}. Показаны ранее загруженные данные.</p>
          <Button type="button" variant="outline" size="sm" onClick={retry}>Повторить</Button>
        </div>
      )}

      <div className="grid min-w-0 items-stretch gap-4 min-[1400px]:grid-cols-[310px_minmax(0,1fr)]">
        <aside className={`${panelClass} p-5`}>
          <div className="flex items-center gap-4">
            <span
              className="flex size-[72px] shrink-0 items-center justify-center rounded-full bg-[#c4efd0] text-2xl font-bold"
              aria-hidden="true"
            >
              {initials}
            </span>
            <h1 className="min-w-0 !text-lg !leading-snug [overflow-wrap:anywhere]">{name}</h1>
          </div>

          <p className="mt-4 text-xs text-[#748079]">
            {roleLabel(profile.role)} · {projectName}
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-solid border-[#d6ded8] px-2.5 py-1 text-[11px]">
              <i className="size-2 rounded-full" style={{backgroundColor: status.color}} aria-hidden="true" />
              {status.label}
            </span>

            {canEdit && (
              <Button type="button" variant="outline" size="xs" className="h-7 text-xs !bg-white" onClick={() => setEditing(true)}>
                <Pencil size={12} aria-hidden="true" />
                Редактировать
              </Button>
            )}
          </div>

          <dl className="mt-7 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-4 text-xs">
            <dt className="text-[#748079]">Email</dt>
            <dd className="m-0 break-words text-right">{profile.email}</dd>

            <dt className="text-[#748079]">Телефон</dt>
            <dd className="m-0 break-words text-right">{profile.phone || '—'}</dd>

            <dt className="text-[#748079]">Telegram</dt>
            <dd className="m-0 break-words text-right">{profile.telegram || '—'}</dd>
          </dl>

          <div className="mt-7 flex flex-wrap gap-2">
            {gitlabUrl && (
              <Button asChild variant="outline" size="sm" className="h-8 text-xs">
                <a href={gitlabUrl} target="_blank" rel="noopener noreferrer">
                  GitLab <ExternalLink size={13} aria-hidden="true" />
                </a>
              </Button>
            )}

            {redmineUrl && (
              <Button asChild variant="outline" size="sm" className="h-8 text-xs">
                <a href={redmineUrl} target="_blank" rel="noopener noreferrer">
                  Redmine <ExternalLink size={13} aria-hidden="true" />
                </a>
              </Button>
            )}
          </div>

          <dl className="mt-8 grid grid-cols-[auto_minmax(0,1fr)] items-center gap-4 text-xs">
            <dt className="text-[#748079]">Отклонение</dt>
            <dd className="m-0 text-right">
              <span className="inline-block rounded-full border border-solid border-[#d6ded8] bg-[#f5f7f6] px-3 py-1">
                {deviationText}
              </span>
            </dd>

            <dt className="text-[#748079]">Факт / план</dt>
            <dd className="m-0 text-right font-bold">
              {number(actual)} / {number(planned)} ч
            </dd>
          </dl>
        </aside>

        <div className="flex min-w-0 flex-col gap-4">
          <div className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
              <article key={stat.title} className={`${panelClass} min-h-[122px] p-4`}>
                <h2 className="m-0 text-[11px] font-normal text-[#748079]">{stat.title}</h2>
                <strong className="mt-3 block break-words text-2xl leading-tight">{stat.value}</strong>

                <p className="mt-2 flex items-start gap-1.5 text-[11px] text-[#748079]">
                  {stat.dot && (
                    <i className="mt-1 size-2 shrink-0 rounded-full" style={{backgroundColor: stat.dot}} aria-hidden="true" />
                  )}
                  <span>{stat.description}</span>
                </p>
              </article>
            ))}
          </div>

          <MemberActivityPanel
            projectId={projectId} memberId={memberId}
            selection={activitySelection} onSelectionChange={setActivitySelection}
            profileRevision={profileRevision}
          />
        </div>
      </div>

      {editing && canEdit && (
        <EditMemberDialog
          projectId={projectId} profile={profile}
          onClose={() => setEditing(false)}
          onSaved={(updatedProfile) => {
            setData((previous) => previous ? {...previous, profile: updatedProfile} : previous)
            setReload((value) => value + 1)
            setProfileRevision((value) => value + 1)
          }}
        />
      )}
    </section>
  )
}