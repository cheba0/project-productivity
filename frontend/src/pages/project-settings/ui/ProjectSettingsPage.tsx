import {useEffect, useRef, useState, type FormEvent} from 'react'
import {Plus} from 'lucide-react'
import {Link, useNavigate, useParams} from 'react-router'

import {Button} from '@/shared/ui/button'
import {Input} from '@/shared/ui/input'

import {getProject, type ProjectDto} from '../../../entities/project'
import {updateProject, type ProjectUpdate} from '../../../entities/project/api/updateProject'
import {useAuthStore} from '../../../store/authStore'
import {useProjectSyncStore} from '../../../store/projectSyncStore'

import {AddMemberDialog} from './AddMemberDialog'
import {ProjectMembersList} from './ProjectMembersList'
import {DeleteProjectDialog} from './DeleteProjectDialog'
import {ProjectArchiveControl} from './ProjectArchiveControl'
import styles from './ProjectSettingsPage.module.css'

interface SettingsForm {
  name: string
  showcaseUrl: string
  startDate: string
  deadline: string
  gitlabUrl: string
  redmineUrl: string
  gitlabToken: string
  redmineToken: string
  sprintWeeks: string
  activeDays: string
  delayedDays: string
}

function toForm(project: ProjectDto): SettingsForm {
  return {
    name: project.name,
    showcaseUrl: project.showcase_url ?? '',
    startDate: project.start_date ?? '',
    deadline: project.deadline ?? '',
    gitlabUrl: project.gitlab_url ?? '',
    redmineUrl: project.redmine_url ?? '',
    gitlabToken: '',
    redmineToken: '',
    sprintWeeks: String(project.sprint_weeks),
    activeDays: String(project.active_after_days),
    delayedDays: String(project.delayed_after_days),
  }
}

function optionalUrl(value: string, label: string): string | null {
  const text = value.trim()
  if (!text) return null

  try {
    const url = new URL(text)

    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
      throw new Error()
    }

    return url.href
  } catch {
    throw new Error(`${label}: укажите корректную ссылку http:// или https:// без логина и пароля.`)
  }
}

function integer(value: string, label: string, min: number, max?: number): number {
  const result = Number(value)

  if (!value.trim() || !Number.isSafeInteger(result) || result < min || (max !== undefined && result > max)) {
    throw new Error(`${label}: введите целое число от ${min}${max === undefined ? '' : ` до ${max}`}.`)
  }

  return result
}

export function ProjectSettingsPage() {
  const {projectId} = useParams()

  if (!projectId) return <p role="alert">Не указан проект.</p>

  return <SettingsLoader key={projectId} projectId={projectId} />
}

function SettingsLoader({projectId}: {projectId: string}) {
  const [project, setProject] = useState<ProjectDto | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    getProject(projectId, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return
        setProject(result)
        setError(null)
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return
        setError(reason instanceof Error ? reason.message : 'Не удалось загрузить настройки.')
      })

    return () => controller.abort()
  }, [projectId, retry])

  if (error) {
    return (
      <div role="alert" className="grid justify-items-start gap-3">
        <p>{error}</p>
        <Button variant="outline" onClick={() => {
          setError(null)
          setRetry((value) => value + 1)
        }}>
          Повторить
        </Button>
        <Link to="/">Вернуться к проектам</Link>
      </div>
    )
  }

  if (!project) return <p role="status">Загрузка настроек проекта…</p>

  return <SettingsEditor initialProject={project} />
}

function SettingsEditor({initialProject}: {initialProject: ProjectDto}) {
  const navigate = useNavigate()
  const [project, setProject] = useState(initialProject)
  const [form, setForm] = useState<SettingsForm>(() => toForm(initialProject))
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [isAddMemberOpen, setIsAddMemberOpen] = useState(false)
  const [isDeleteProjectOpen, setIsDeleteProjectOpen] = useState(false)
  const [archiveBusy, setArchiveBusy] = useState(false)

  const submitting = useRef(false)
  const userEmail = useAuthStore((state) => state.user?.email)

  const canManage = project.members.some((member) =>
    member.is_owner && member.email.trim().toLowerCase() === userEmail?.trim().toLowerCase(),
  )

  function change(field: keyof SettingsForm, value: string) {
    setForm((previous) => ({...previous, [field]: value}))
    setSaveMessage(null)
    setSaveError(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canManage || submitting.current || archiveBusy) return

    setSaveError(null)
    setSaveMessage(null)

    try {
      const name = form.name.trim()
      if (!name) throw new Error('Укажите название проекта.')
      if (name.length > 255) throw new Error('Название не должно превышать 255 символов.')

      const sprintWeeks = integer(form.sprintWeeks, 'Длина спринта', 1, 12)
      const activeDays = integer(form.activeDays, 'Порог активности', 0)
      const delayedDays = integer(form.delayedDays, 'Порог замедления', 1)

      if (delayedDays <= activeDays) {
        throw new Error('Порог замедления должен быть больше порога активности.')
      }

      const startDate = form.startDate || null
      const deadline = form.deadline || null

      if (startDate && deadline && deadline < startDate) {
        throw new Error('Дата завершения не может быть раньше даты начала.')
      }

      const showcaseUrl = optionalUrl(form.showcaseUrl, 'Витрина')
      const gitlabUrl = optionalUrl(form.gitlabUrl, 'GitLab')
      const redmineUrl = optionalUrl(form.redmineUrl, 'Redmine')
      const gitlabToken = form.gitlabToken.trim()
      const redmineToken = form.redmineToken.trim()

      if (gitlabToken && !gitlabUrl) throw new Error('Для токена GitLab нужна ссылка на проект.')
      if (redmineToken && !redmineUrl) throw new Error('Для токена Redmine нужна ссылка на проект.')

      const candidate = {
        name,
        showcase_url: showcaseUrl,
        gitlab_url: gitlabUrl,
        redmine_url: redmineUrl,
        start_date: startDate,
        deadline,
        sprint_weeks: sprintWeeks,
        active_after_days: activeDays,
        delayed_after_days: delayedDays,
      }

      // Отправляем только изменённые поля.
      const payload: ProjectUpdate = {}

      if (candidate.name !== project.name) payload.name = candidate.name
      if (candidate.showcase_url !== project.showcase_url) payload.showcase_url = candidate.showcase_url
      if (candidate.gitlab_url !== project.gitlab_url) payload.gitlab_url = candidate.gitlab_url
      if (candidate.redmine_url !== project.redmine_url) payload.redmine_url = candidate.redmine_url
      if (candidate.start_date !== project.start_date) payload.start_date = candidate.start_date
      if (candidate.deadline !== project.deadline) payload.deadline = candidate.deadline
      if (candidate.sprint_weeks !== project.sprint_weeks) payload.sprint_weeks = candidate.sprint_weeks
      if (candidate.active_after_days !== project.active_after_days) payload.active_after_days = candidate.active_after_days
      if (candidate.delayed_after_days !== project.delayed_after_days) payload.delayed_after_days = candidate.delayed_after_days
      if (gitlabToken) payload.gitlab_token = gitlabToken
      if (redmineToken) payload.redmine_token = redmineToken

      if (Object.keys(payload).length === 0) {
        setSaveMessage('Изменений нет.')
        return
      }

      const needsSync =
        payload.gitlab_url !== undefined || payload.redmine_url !== undefined ||
        payload.gitlab_token !== undefined || payload.redmine_token !== undefined ||
        payload.start_date !== undefined

      submitting.current = true
      setSaving(true)

      const updated = await updateProject(project.id, payload)

      setProject(updated)
      setForm(toForm(updated))
      useProjectSyncStore.getState().invalidateProjects()
      setSaveMessage(needsSync
        ? 'Настройки сохранены. Нажмите «Обновить данные», чтобы загрузить показатели с новыми настройками.'
        : 'Настройки сохранены.')
    } catch (reason: unknown) {
      setSaveError(reason instanceof Error ? reason.message : 'Не удалось сохранить настройки.')
    } finally {
      submitting.current = false
      setSaving(false)
    }
  }

  const disabled = !canManage || saving || archiveBusy
  const fieldClass = 'grid gap-2 text-xs'
  const inputClass = 'h-9 bg-white'

  return (
    <section className={styles.page} aria-labelledby="settings-title">
      <header className={styles.heading}>
        <h1 id="settings-title">Настройки проекта</h1>
        <p>{project.name}</p>
      </header>

      {!canManage && (
        <p className="text-sm text-[#748079]">
          Изменять настройки может только владелец проекта.
        </p>
      )}

      <form className={styles.form} onSubmit={handleSubmit} aria-busy={saving}>
        <div className={styles.columns}>
          <div className={styles.column}>
            <section className={styles.panel} aria-labelledby="basic-title">
              <h2 id="basic-title">Основное</h2>

              <div className="grid gap-4">
                <label className={fieldClass}>
                  <span>Название проекта</span>
                  <Input
                    value={form.name} onChange={(event) => change('name', event.target.value)}
                    maxLength={255} required disabled={disabled} className={inputClass}
                    placeholder="Название проекта"
                  />
                </label>

                <label className={fieldClass}>
                  <span>Ссылка на витрину проектов</span>
                  <Input
                    type="url" value={form.showcaseUrl}
                    onChange={(event) => change('showcaseUrl', event.target.value)}
                    disabled={disabled} className={inputClass} placeholder="https://..."
                  />
                </label>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-3 text-sm text-[#58655e]">
                  <span>Сроки проекта</span>

                  <label className="flex items-center gap-3">
                    <span>от</span>
                    <Input
                      type="date" value={form.startDate}
                      onChange={(event) => change('startDate', event.target.value)}
                      disabled={disabled} aria-label="Дата начала проекта"
                      className="h-10 w-[110px] rounded-full border-[#cbd4ce] bg-white px-3 text-center text-sm text-[#85918a] [&::-webkit-calendar-picker-indicator]:hidden"
                    />
                  </label>

                  <label className="flex items-center gap-3">
                    <span>до</span>
                    <Input
                      type="date" value={form.deadline} min={form.startDate || undefined}
                      onChange={(event) => change('deadline', event.target.value)}
                      disabled={disabled} aria-label="Дата завершения проекта"
                      className="h-10 w-[110px] rounded-full border-[#cbd4ce] bg-white px-3 text-center text-sm text-[#85918a] [&::-webkit-calendar-picker-indicator]:hidden"
                    />
                  </label>
                </div>
              </div>
            </section>

            <section className={styles.panel} aria-labelledby="thresholds-title">
              <h2 id="thresholds-title">Спринты и статусы</h2>

              <div className="grid gap-5 text-xs">
                <label className="flex items-center justify-between gap-3">
                  <span>Длина спринта</span>
                  <span className="flex items-center gap-2">
                    <Input
                      type="number" min={1} max={12} step={1} required
                      value={form.sprintWeeks}
                      onChange={(event) => change('sprintWeeks', event.target.value)}
                      disabled={disabled} className="h-8 w-16 text-center"
                    />
                    нед.
                  </span>
                </label>

                <h3 className="m-0 text-xs font-semibold">Дни без активности в GitLab и Redmine</h3>

                <label className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2">
                    <i className="size-2 shrink-0 rounded-full bg-[#22bf45]" aria-hidden="true" />
                    Идёт работа / Активен
                  </span>
                  <span className="flex items-center gap-2">
                    до
                    <Input
                      type="number" min={0} step={1} required value={form.activeDays}
                      onChange={(event) => change('activeDays', event.target.value)}
                      disabled={disabled} className="h-8 w-16 text-center"
                    />
                    дн.
                  </span>
                </label>

                <label className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2">
                    <i className="size-2 shrink-0 rounded-full bg-[#ffb600]" aria-hidden="true" />
                    Замедление
                  </span>
                  <span className="flex items-center gap-2">
                    до
                    <Input
                      type="number" min={1} step={1} required value={form.delayedDays}
                      onChange={(event) => change('delayedDays', event.target.value)}
                      disabled={disabled} className="h-8 w-16 text-center"
                    />
                    дн.
                  </span>
                </label>

                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2">
                    <i className="size-2 shrink-0 rounded-full bg-[#ff4265]" aria-hidden="true" />
                    Без активности
                  </span>
                  <span>Более {form.delayedDays || '—'} дн.</span>
                </div>
              </div>
            </section>
          </div>

          <div className={styles.column}>
            <section className={styles.panel} aria-labelledby="integrations-title">
              <h2 id="integrations-title">Интеграции</h2>

              <div className="grid gap-5 sm:grid-cols-2">
                <fieldset className="m-0 grid min-w-0 gap-3 border-0 p-0">
                  <legend className="mb-3 text-sm font-bold">GitLab</legend>

                  <label className={fieldClass}>
                    <span>Ссылка на проект</span>
                    <Input
                      type="url" value={form.gitlabUrl}
                      onChange={(event) => change('gitlabUrl', event.target.value)}
                      disabled={disabled} className={inputClass} placeholder="https://gitlab.com/group/project"
                    />
                  </label>

                  <label className={fieldClass}>
                    <span>{project.gitlab_token_configured ? 'Новый токен, если нужно заменить' : 'Токен'}</span>
                    <Input
                      type="password" value={form.gitlabToken} autoComplete="new-password"
                      onChange={(event) => change('gitlabToken', event.target.value)}
                      disabled={disabled} className={inputClass}
                      placeholder={project.gitlab_token_configured ? 'Токен сохранён' : 'Введите токен'}
                    />
                  </label>
                </fieldset>

                <fieldset className="m-0 grid min-w-0 gap-3 border-0 p-0">
                  <legend className="mb-3 text-sm font-bold">Redmine</legend>

                  <label className={fieldClass}>
                    <span>Ссылка на проект</span>
                    <Input
                      type="url" value={form.redmineUrl}
                      onChange={(event) => change('redmineUrl', event.target.value)}
                      disabled={disabled} className={inputClass} placeholder="https://redmine.../projects/..."
                    />
                  </label>

                  <label className={fieldClass}>
                    <span>{project.redmine_token_configured ? 'Новый токен, если нужно заменить' : 'Токен'}</span>
                    <Input
                      type="password" value={form.redmineToken} autoComplete="new-password"
                      onChange={(event) => change('redmineToken', event.target.value)}
                      disabled={disabled} className={inputClass}
                      placeholder={project.redmine_token_configured ? 'Токен сохранён' : 'Введите токен'}
                    />
                  </label>
                </fieldset>
              </div>

            </section>

            <section className={styles.panel} aria-labelledby="members-title">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 id="members-title" className="!m-0">Участники · {project.members.length}</h2>
                <Button
                  type="button" variant="outline" size="sm" disabled={disabled}
                  onClick={() => setIsAddMemberOpen(true)}
                >
                  <Plus size={15} aria-hidden="true" />
                  Добавить участника
                </Button>
              </div>

              <ProjectMembersList
                projectId={project.id} members={project.members}
                canManage={canManage} disabled={saving}
                onRemoved={(memberId) => {
                  setProject((previous) => ({
                    ...previous,
                    members: previous.members.filter((member) => member.id !== memberId),
                  }))
                }}
              />
            </section>
          </div>
        </div>

        {saveError && <p role="alert" className="px-1 text-sm text-[#b42318]">{saveError}</p>}
        {saveMessage && <p role="status" className="px-1 text-sm text-[#16852f]">{saveMessage}</p>}

        <footer className={styles.actions}>
          <div className={styles.primaryActions}>
            <Button
              type="submit" variant="outline" disabled={disabled}
              className="border-[#22bf45] bg-[#e6f7eb] text-[#18201c] hover:bg-[#d8f2df]"
            >
              {saving ? 'Сохраняем…' : 'Сохранить'}
            </Button>

            <Button
              type="button" variant="outline" disabled={saving || archiveBusy}
              onClick={() => {
                const index = window.history.state?.idx

                if (typeof index === 'number' && index > 0) {
                  navigate(-1)
                } else {
                  navigate(`/projects/${project.id}`, {replace: true})
                }
              }}
            >
              Отмена
            </Button>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <ProjectArchiveControl
              project={project} canManage={canManage} disabled={saving}
              onBusyChange={setArchiveBusy}
              onChanged={(updated) => {
                setProject((previous) => ({
                  ...previous,
                  archived_at: updated.archived_at,
                  status: updated.status,
                  status_label: updated.status_label,
                  updated_at: updated.updated_at,
                }))
              }}
            />

            <button
              className={styles.deleteButton} type="button" disabled={disabled}
              onClick={() => setIsDeleteProjectOpen(true)}
            >
              Удалить проект
            </button>
          </div>
        </footer>
      </form>

      <DeleteProjectDialog
        projectId={project.id} projectName={project.name}
        open={isDeleteProjectOpen} onClose={() => setIsDeleteProjectOpen(false)}
      />

      <AddMemberDialog
        projectId={project.id} open={isAddMemberOpen}
        onClose={() => setIsAddMemberOpen(false)}
        onAdded={(member) => {
          setProject((previous) => ({
            ...previous,
            members: [...previous.members.filter((item) => item.id !== member.id), member],
          }))
        }}
      />
    </section>
  )
}