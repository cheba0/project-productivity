import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import { Button } from '@/shared/ui/button'
import {getProject, getProjectSprints, type ProjectSprint} from '../../../entities/project'
import { useAuthStore } from '../../../store/authStore'
import { EditMemberDialog } from './EditMemberDialog'
import {getMemberDashboard, type MemberDashboard,} from '../../../entities/project/api/getMemberDashboard'
import {getProjectSyncStatus,} from '../../../entities/project/api/syncProject'
import { useProjectSyncStore } from '../../../store/projectSyncStore'
import { createPortal } from 'react-dom'
import { ChevronLeft, ChevronRight } from 'lucide-react'

import { useProjectHeaderStore } from '../../../store/projectHeaderStore'

const numberFormat = new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 2,})

function hours(value: number | null): string {
  return value === null ? '—' : `${numberFormat.format(value)} ч`
}

function activity(days: number | null): string {
  if (days === null) return 'Нет данных'
  if (days === 0) return 'Сегодня'
  if (days === 1) return 'Вчера'
  return `${days} дн. назад`
}

function statusLabel(value: string): string {
  switch (value) {
    case 'working':
      return 'Активен'
    case 'partial':
      return 'Частично'
    case 'delayed':
      return 'Замедление'
    case 'idle':
      return 'Без активности'
    default:
      return 'Нет данных'
  }
}

function profileUrl(value: string | null): string | null {
  if (!value) return null

  try {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol)
      ? url.href
      : null
  } catch {
    return null
  }
}

function dateOnly(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

export function MemberPage() {
  const { projectId, memberId } = useParams()

  if (!projectId || !memberId) {
    return <p role="alert">Не указан проект или участник.</p>
  }

  return (
    <MemberDetails
      key={`${projectId}:${memberId}`}
      projectId={projectId}
      memberId={memberId}
    />
  )
}

function MemberDetails({
  projectId,
  memberId,
}: {
  projectId: string
  memberId: string
}) {
  const [editing, setEditing] = useState(false)
  const [ownerEmail, setOwnerEmail] = useState<string | null>(null)
  const userEmail = useAuthStore((state) => state.user?.email)
  const [data, setData] = useState<MemberDashboard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const [period, setPeriod] = useState('all')
  const [sprints, setSprints] = useState<ProjectSprint[]>([])
  const [periodNotice, setPeriodNotice] = useState<string | null>(null)
  const headerControlsElement = useProjectHeaderStore((state) => state.controlsElement)

  const syncRevision = useProjectSyncStore(
    (state) => state.revision,
  )

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

        if (!sync.has_cached_data || !sync.period) {
          throw new Error(
            'Данные ещё не загружены. Нажмите «Обновить данные».',
          )
        }

        const available = sync.period

        let requestedStart = available.start
        let requestedEnd = available.end

        if (period === 'recent') {
          const end = new Date()
          const start = new Date(end)

          start.setDate(start.getDate() - 29)

          requestedStart = dateOnly(start)
          requestedEnd = dateOnly(end)
        } else if (period !== 'all') {
          const sprint = sprintData.items.find(
            (item) => String(item.number) === period,
          )

          if (!sprint) {
            throw new Error('Выбранный спринт не найден.')
          }

          requestedStart = sprint.start
          requestedEnd = sprint.end
        }

        const start =
          requestedStart < available.start
            ? available.start
            : requestedStart

        const end =
          requestedEnd > available.end
            ? available.end
            : requestedEnd

        // Сохраняем список даже если в выбранном спринте нет данных:
        // пользователь сможет переключиться на другой период.
        setSprints(sprintData.items)

        if (start > end) {
          throw new Error(
            'За выбранный период нет сохранённых данных.',
          )
        }

        const result = await getMemberDashboard(
          projectId,
          memberId,
          { start, end },
          controller.signal,
        )

        if (controller.signal.aborted) return

        const notices: string[] = []

        if (start !== requestedStart || end !== requestedEnd) {
          const format = (value: string) =>
            new Intl.DateTimeFormat('ru-RU').format(
              new Date(`${value}T00:00:00`),
            )

          notices.push(
            `Данные доступны за часть периода: ` +
            `${format(start)} — ${format(end)}.`,
          )
        }

        if (sync.last_error) {
          notices.push(
            'Последняя синхронизация завершилась ошибкой. ' +
            'Показаны ранее сохранённые данные.',
          )
        }

        setOwnerEmail(
          project.members.find((member) => member.is_owner)?.email ??
            null,
        )

        setData(result)
        setError(null)
        setPeriodNotice(notices.length ? notices.join(' ') : null)
      } catch (reason: unknown) {
        if (controller.signal.aborted) return

        setError(
          reason instanceof Error
            ? reason.message
            : 'Не удалось загрузить участника.',
        )
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

  const sprintIndex = sprints.findIndex(
    (item) => String(item.number) === period,
  )

  const previousSprint =
    sprintIndex > 0 ? sprints[sprintIndex - 1] : undefined

  const nextSprint =
    sprintIndex >= 0 ? sprints[sprintIndex + 1] : undefined

  const periodControls = headerControlsElement
    ? createPortal(
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-8"
            disabled={!previousSprint}
            aria-label="Предыдущий спринт"
            onClick={() => {
              if (previousSprint) {
                changePeriod(String(previousSprint.number))
              }
            }}
          >
            <ChevronLeft size={16} aria-hidden="true" />
          </Button>

          <select
            className="h-8 max-w-[200px] rounded-md border border-solid border-[#cbd4ce] bg-white px-3 text-xs text-[#18201c]"
            aria-label="Период показателей участника"
            value={period}
            onChange={(event) => changePeriod(event.target.value)}
          >
            <option value="all">Весь доступный период</option>
            <option value="recent">Последние 30 дней</option>

            {sprints.map((sprint) => (
              <option key={sprint.number} value={sprint.number}>
                Спринт {sprint.number}
              </option>
            ))}
          </select>

          <Button
            type="button"
            variant="outline"
            size="icon"
            className="size-8"
            disabled={!nextSprint}
            aria-label="Следующий спринт"
            onClick={() => {
              if (nextSprint) {
                changePeriod(String(nextSprint.number))
              }
            }}
          >
            <ChevronRight size={16} aria-hidden="true" />
          </Button>
        </div>,
        headerControlsElement,
      )
    : null

  if (!data) {
    return (
      <>
        {periodControls}

        {error ? (
          <div role="alert" className="grid justify-items-start gap-3">
            <p>{error}</p>

            <Button
              variant="outline"
              onClick={() => {
                setError(null)
                setReload((value) => value + 1)
              }}
            >
              Повторить
            </Button>

            <Link to={`/projects/${projectId}`}>
              Вернуться к проекту
            </Link>
          </div>
        ) : (
          <p role="status">Загрузка участника…</p>
        )}
      </>
    )
  }

  const { profile, summary } = data
  const normalizedEmail = userEmail?.trim().toLowerCase()

  const canEdit = Boolean(
    normalizedEmail &&
    (
      normalizedEmail === profile.email.trim().toLowerCase() ||
      normalizedEmail === ownerEmail?.trim().toLowerCase()
    ),
  )

  const name = profile.name || profile.email
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()

  const redmineAvailable =
    data.sources.redmine !== 'not_configured'

  const redmineLinked =
    redmineAvailable && profile.redmine_user_id !== null

  const gitlabUrl = profileUrl(profile.gitlab_profile_url)
  const redmineUrl = profileUrl(profile.redmine_profile_url)

  const stats = [
    {
      title: 'Выполнено',
      value: redmineLinked ? summary.tasks_done ?? '—' : '—',
      description: redmineLinked
        ? `Всего назначено: ${summary.tasks_total ?? '—'} задач`
        : 'Нужна привязка к Redmine',
    },
    {
      title: 'Незавершённые задачи',
      value: redmineLinked
        ? summary.tasks_in_progress ?? '—'
        : '—',
      description: 'В выбранной выборке',
    },
    {
      title: 'Активность · GitLab',
      value: data.sources.gitlab === 'not_configured'
        ? 'Не подключён'
        : activity(summary.gitlab_inactive_days),
      description: `Коммитов за период: ${summary.commits}`,
    },
    {
      title: 'Активность · Redmine',
      value: !redmineAvailable
        ? 'Не подключён'
        : !redmineLinked
          ? 'Не привязан'
          : activity(summary.redmine_inactive_days),
      description: redmineLinked
        ? `Записей трудозатрат: ${summary.redmine_entries ?? '—'}`
        : 'Укажите Redmine ID в профиле',
    },
  ]

  return (
    <section className="grid min-w-0 gap-5">
      {periodControls}

      {periodNotice && (
        <p
          role="status"
          className="rounded-lg bg-[#fff5df] p-3 text-xs text-[#815d12]"
        >
          {periodNotice}
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-[#b42318]">
          Не удалось обновить показатели: {error}.
          Показаны ранее загруженные данные.
        </p>
      )}

      <div className="grid min-w-0 items-start gap-5 xl:grid-cols-[290px_minmax(0,1fr)]">
        <aside className="min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-5">
          <div className="flex items-center gap-4">
            <span
              className="flex size-16 shrink-0 items-center justify-center rounded-full bg-[#c4efd0] text-2xl font-bold"
              aria-hidden="true"
            >
              {initials}
            </span>

            <h1 className="!text-lg !leading-snug break-words">
              {name}
            </h1>
          </div>

          <p className="mt-4 text-xs text-[#748079]">
            {profile.role === 'owner'
              ? 'Владелец проекта'
              : profile.role}
          </p>

          <span className="mt-3 inline-flex rounded-full border border-solid border-[#d6ded8] px-3 py-1 text-xs">
            {statusLabel(summary.activity_status)}
          </span>
          {canEdit && (
            <div className="mt-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setEditing(true)}
              >
                Редактировать
              </Button>
            </div>
          )}

          <dl className="mt-6 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-4 text-xs">
            <dt className="text-[#748079]">Email</dt>
            <dd className="m-0 break-words text-right">
              {profile.email}
            </dd>

            <dt className="text-[#748079]">Телефон</dt>
            <dd className="m-0 text-right">
              {profile.phone || '—'}
            </dd>

            <dt className="text-[#748079]">Telegram</dt>
            <dd className="m-0 break-words text-right">
              {profile.telegram || '—'}
            </dd>
          </dl>

          <div className="mt-5 flex flex-wrap gap-2">
            {gitlabUrl && (
              <Button asChild variant="outline" size="sm">
                <a
                  href={gitlabUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitLab ↗
                </a>
              </Button>
            )}

            {redmineUrl && (
              <Button asChild variant="outline" size="sm">
                <a
                  href={redmineUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Redmine ↗
                </a>
              </Button>
            )}
          </div>

          <dl className="mt-6 grid grid-cols-2 gap-4 text-xs">
            <dt className="text-[#748079]">Факт / план</dt>
            <dd className="m-0 text-right font-semibold">
              {hours(redmineLinked ? summary.actual_hours : null)}
              {' / '}
              {hours(redmineLinked ? summary.planned_hours : null)}
            </dd>

            <dt className="text-[#748079]">Отклонение</dt>
            <dd className="m-0 text-right">
              {!redmineLinked ||
              summary.hours_deviation_percent === null
                ? '—'
                : `${summary.hours_deviation_percent > 0 ? '+' : ''}${numberFormat.format(summary.hours_deviation_percent)}%`}
            </dd>
          </dl>
        </aside>

        <div className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-4">
          {stats.map((stat) => (
            <article
              key={stat.title}
              className="min-w-0 rounded-2xl border border-solid border-[#e3e8e5] bg-white p-4"
            >
              <h2 className="m-0 text-xs font-normal text-[#748079]">
                {stat.title}
              </h2>

              <strong className="mt-3 block break-words text-2xl">
                {stat.value}
              </strong>

              <p className="mt-2 text-xs text-[#748079]">
                {stat.description}
              </p>
            </article>
          ))}
        </div>
      </div>
      {editing && canEdit && (
        <EditMemberDialog
          projectId={projectId}
          profile={profile}
          onClose={() => setEditing(false)}
          onSaved={(updatedProfile) => {
            setData((previous) =>
              previous
                ? { ...previous, profile: updatedProfile }
                : previous,
            )

            setReload((value) => value + 1)
          }}
        />
      )}
    </section>
  )
}