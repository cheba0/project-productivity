import { useEffect, useState } from 'react'
import { Plus, X } from 'lucide-react'
import { Link, useLocation, useParams } from 'react-router'
import {getProject, type ProjectDto} from '../../../entities/project'
import { useAuthStore } from '../../../store/authStore'
import styles from './ProjectSettingsPage.module.css'
import { AddMemberDialog } from './AddMemberDialog'
import { DeleteProjectDialog } from './DeleteProjectDialog'

function getInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

export function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const userEmail = useAuthStore((state) => state.user?.email)
  const [loadedProject, setLoadedProject] = useState<ProjectDto | null>(null)
  const [membersError, setMembersError] = useState<string | null>(null)
  const [membersReload, setMembersReload] = useState(0)
  useEffect(() => {
    if (!projectId) return

    const controller = new AbortController()

    getProject(projectId, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return

        setLoadedProject(result)
        setMembersError(null)
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return

        setMembersError(
          reason instanceof Error
            ? reason.message
            : 'Не удалось загрузить участников.',
        )
      })

    return () => controller.abort()
  }, [projectId, membersReload])

  const currentProject =
    loadedProject?.id === projectId ? loadedProject : null

  const members = currentProject?.members ?? []

  const canManageMembers = members.some(
    (member) =>
      member.is_owner &&
      member.email.toLowerCase() === userEmail?.toLowerCase(),
  )
  const location = useLocation()
  const routeState: unknown = location.state

  const routeProjectName =
    typeof routeState === 'object' &&
    routeState !== null &&
    'projectName' in routeState &&
    typeof routeState.projectName === 'string'
        ? routeState.projectName
        : ''

  const projectName = currentProject?.name || routeProjectName
  const [warningDays, setWarningDays] = useState('7')
  const [isAddMemberOpen, setIsAddMemberOpen] = useState(false)
  const [isDeleteProjectOpen, setIsDeleteProjectOpen] = useState(false)

  return (
    <section className={styles.page} aria-labelledby="settings-title">
      <header className={styles.heading}>
        <h1 id="settings-title">Настройки проекта</h1>
        <p>{projectName || `Проект ${projectId}`}</p>
      </header>

      <form
        className={styles.form}
        onSubmit={(event) => event.preventDefault()}
      >
        <div className={styles.columns}>
          <div className={styles.column}>
            <section className={styles.panel} aria-labelledby="basic-title">
              <h2 id="basic-title">Основное</h2>

              <label className={styles.field}>
                <span>Название проекта</span>
                <input
                    key={projectId}
                    name="name"
                    type="text"
                    defaultValue={projectName}
                    placeholder="Название проекта"
                />
              </label>

              <label className={styles.field}>
                <span>Ссылка на витрину проектов</span>
                <input
                  name="showcaseUrl"
                  type="url"
                  placeholder="https://showcase.tpu.ru/..."
                />
              </label>

              <div className={styles.dates}>
                <span>Сроки проекта</span>

                <label className={styles.dateField}>
                  <span>от</span>
                  <input
                    name="startDate"
                    type="date"
                    aria-label="Дата начала проекта"
                  />
                </label>

                <label className={styles.dateField}>
                  <span>до</span>
                  <input
                    name="deadline"
                    type="date"
                    aria-label="Дата завершения проекта"
                  />
                </label>
              </div>

              <label className={styles.pauseRow}>
                <span>Поставить проект на паузу</span>

                <input
                  className={styles.switch}
                  type="checkbox"
                  role="switch"
                  disabled
                  title="Изменение состояния проекта пока не подключено"
                />
              </label>
            </section>

            <section
              className={`${styles.panel} ${styles.thresholdsPanel}`}
              aria-labelledby="thresholds-title"
            >
              <h2 id="thresholds-title">Спринты и статусы</h2>
              <div className={styles.statusRow}>
                <label htmlFor="settings-sprint-weeks">Длина спринта</label>

                <div className={styles.threshold}>
                  <input
                    id="settings-sprint-weeks"
                    name="sprintWeeks"
                    type="number"
                    min="1"
                    max="12"
                    step="1"
                    defaultValue="1"
                  />
                  <span>нед.</span>
                </div>
              </div>

              <p className={styles.hint}>По умолчанию — 1 неделя</p>

              <h3 className={styles.subheading}>
                Дни без активности в GitLab и Redmine
              </h3>


              <div className={styles.statusRow}>
                <label className={styles.statusLabel} htmlFor="active-days">
                  <span
                    className={`${styles.dot} ${styles.green}`}
                    aria-hidden="true"
                  />
                  Идёт работа / Активен
                </label>

                <div className={styles.threshold}>
                  <span>до</span>
                  <input
                    id="active-days"
                    name="activeDays"
                    type="number"
                    min="1"
                    step="1"
                    defaultValue="3"
                  />
                  <span>дн.</span>
                </div>
              </div>

              <div className={styles.statusRow}>
                <label className={styles.statusLabel} htmlFor="warning-days">
                  <span
                    className={`${styles.dot} ${styles.yellow}`}
                    aria-hidden="true"
                  />
                  Замедление
                </label>

                <div className={styles.threshold}>
                  <span>до</span>
                  <input
                    id="warning-days"
                    name="warningDays"
                    type="number"
                    min="1"
                    step="1"
                    value={warningDays}
                    onChange={(event) => setWarningDays(event.target.value)}
                  />
                  <span>дн.</span>
                </div>
              </div>

              <div className={styles.statusRow}>
                <span className={styles.statusLabel}>
                  <span
                    className={`${styles.dot} ${styles.red}`}
                    aria-hidden="true"
                  />
                  Простой
                </span>

                <span className={styles.hint}>
                  более {warningDays || '—'} дн.
                </span>
              </div>
            </section>
          </div>

          <div className={styles.column}>
            <section
              className={styles.panel}
              aria-labelledby="integrations-title"
            >
              <h2 id="integrations-title">Интеграции</h2>

              <div className={styles.integrations}>
                <fieldset className={styles.integration}>
                  <legend>GitLab</legend>

                  <label className={styles.field}>
                    <span>Ссылка</span>
                    <input
                      name="gitlabUrl"
                      type="url"
                      placeholder="https://gitlab.tpu.ru/..."
                    />
                  </label>

                  <label className={styles.field}>
                    <span>Токен</span>
                    <input
                      name="gitlabToken"
                      type="password"
                      placeholder="Введите токен"
                      autoComplete="off"
                    />
                  </label>
                </fieldset>

                <fieldset className={styles.integration}>
                  <legend>Redmine</legend>

                  <label className={styles.field}>
                    <span>Ссылка</span>
                    <input
                      name="redmineUrl"
                      type="url"
                      placeholder="https://redmine.tpu.ru/..."
                    />
                  </label>

                  <label className={styles.field}>
                    <span>Токен</span>
                    <input
                      name="redmineToken"
                      type="password"
                      placeholder="Введите токен"
                      autoComplete="off"
                    />
                  </label>
                </fieldset>
              </div>
            </section>

            <section
              className={`${styles.panel} ${styles.membersPanel}`}
              aria-labelledby="members-title"
            >
              <div className={styles.panelHeading}>
                <h2 id="members-title">
                  Участники · {currentProject ? members.length : '…'}
                </h2>

                <button
                    className={styles.addButton}
                    type="button"
                    onClick={() => setIsAddMemberOpen(true)}
                    disabled={!canManageMembers}
                >
                    <Plus size={16} aria-hidden="true" />
                    Добавить участника
                </button>
              </div>

              {membersError ? (
                <div role="alert">
                  <p>{membersError}</p>

                  <button
                    type="button"
                    className="button"
                    onClick={() => {
                      setMembersError(null)
                      setMembersReload((value) => value + 1)
                    }}
                  >
                    Повторить
                  </button>
                </div>
              ) : !currentProject ? (
                <p role="status">Загрузка участников…</p>
              ) : null}

              <ul className={styles.members}>
                {members.map((member, index) => (
                  <li className={styles.member} key={member.id}>
                    <span
                      className={styles.avatar}
                      data-color={index % 4}
                      aria-hidden="true"
                    >
                      {getInitials(member.name || member.email)}
                    </span>

                    <div className={styles.memberInfo}>
                      <span className={styles.memberName}>
                        {member.name || member.email}
                      </span>
                      <span className={styles.memberRole}>
                        {member.role}
                      </span>
                    </div>

                    <button
                      className={styles.removeButton}
                      type="button"
                      disabled
                      aria-label={`Удалить участника: ${member.name || member.email}`}
                      title="Удаление участников пока недоступно"
                    >
                      <X size={20} aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </div>

        <footer className={styles.actions}>
          <div className={styles.primaryActions}>
            <button
              className={styles.saveButton}
              type="button"
              disabled
              title="Сохранение пока не подключено"
            >
              Сохранить
            </button>

            <Link className={styles.cancelButton} to="/">
              Отмена
            </Link>
          </div>

          <button
            className={styles.deleteButton}
            type="button"
            onClick={() => setIsDeleteProjectOpen(true)}
            >
            Удалить проект
          </button>
        </footer>
      </form>
      <DeleteProjectDialog
        open={isDeleteProjectOpen}
        projectName={projectName}
        onClose={() => setIsDeleteProjectOpen(false)}
      />
      {projectId && (
        <AddMemberDialog
          key={projectId}
          projectId={projectId}
          open={isAddMemberOpen}
          onClose={() => setIsAddMemberOpen(false)}
          onAdded={(member) => {
            setLoadedProject((previous) => {
              if (!previous || previous.id !== projectId) {
                return previous
              }

              return {
                ...previous,
                members: [
                  ...previous.members.filter(
                    (item) => item.id !== member.id,
                  ),
                  member,
                ],
              }
            })
          }}
        />
      )}
    </section>
  )
}