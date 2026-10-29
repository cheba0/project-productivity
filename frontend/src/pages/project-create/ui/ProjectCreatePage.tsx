import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import {
  createProject,
  getProjectLiveCard,
  ProjectLoadingCard,
  type CreatedProject,
  type ProjectLiveCard,
} from '../../../entities/project'

import styles from './ProjectCreatePage.module.css'

export function ProjectCreatePage() {
  const [warningDays, setWarningDays] = useState('7')
  const [startDate, setStartDate] = useState('')

  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const [createdProject, setCreatedProject] =
    useState<CreatedProject | null>(null)

  const [loadingData, setLoadingData] = useState(false)
  const [dataError, setDataError] = useState<string | null>(null)
  const [liveCard, setLiveCard] = useState<ProjectLiveCard | null>(null)

  async function loadProjectData(projectId: string) {
    setLoadingData(true)
    setDataError(null)

    try {
      const result = await getProjectLiveCard(projectId)
      setLiveCard(result)
    } catch (error) {
      setDataError(
        error instanceof Error
          ? error.message
          : 'Не удалось загрузить данные интеграций.',
      )
    } finally {
      setLoadingData(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (saving || createdProject) return

    const formData = new FormData(event.currentTarget)

    const getText = (field: string) =>
      String(formData.get(field) ?? '').trim()

    const name = getText('name')
    const activeDays = Number(getText('activeDays'))
    const delayedDays = Number(getText('warningDays'))
    const sprintWeeks = Number(getText('sprintWeeks'))

    const start = getText('startDate')
    const deadline = getText('deadline')

    const redmineUrl = getText('redmineUrl')
    const redmineToken = getText('redmineToken')

    setSaveError(null)

    if (!name) {
      setSaveError('Введите название проекта.')
      return
    }

    if (
      !Number.isInteger(activeDays) ||
      !Number.isInteger(delayedDays) ||
      activeDays < 0 ||
      delayedDays <= activeDays
    ) {
      setSaveError(
        'Порог замедления должен быть больше порога активной работы.',
      )
      return
    }

    if (
      !Number.isInteger(sprintWeeks) ||
      sprintWeeks < 1 ||
      sprintWeeks > 12
    ) {
      setSaveError('Длина спринта должна быть от 1 до 12 недель.')
      return
    }

    if (start && deadline && deadline < start) {
      setSaveError('Дата завершения не может быть раньше даты начала.')
      return
    }

    if (Boolean(redmineUrl) !== Boolean(redmineToken)) {
      setSaveError(
        'Для Redmine заполните ссылку и токен либо оставьте оба поля пустыми.',
      )
      return
    }

    setSaving(true)

    try {
      const project = await createProject({
        name,
        showcase_url: getText('showcaseUrl') || null,
        gitlab_url: getText('gitlabUrl'),
        gitlab_token: getText('gitlabToken'),
        redmine_url: redmineUrl || null,
        redmine_token: redmineToken || null,
        start_date: start || null,
        deadline: deadline || null,
        sprint_weeks: sprintWeeks,
        active_after_days: activeDays,
        delayed_after_days: delayedDays,
      })

      setCreatedProject(project)
      await loadProjectData(project.id)
    } catch (error) {
      setSaveError(
        error instanceof Error
          ? error.message
          : 'Не удалось получить подтверждение создания проекта.',
      )
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className={styles.page} aria-labelledby="create-title">
      <header className={styles.heading}>
        <h1 id="create-title">Новый проект</h1>
        <p>Данные загрузятся через некоторое время после создания</p>
      </header>

      {!createdProject ? (
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.columns}>
            <fieldset className={styles.fields} disabled={saving}>
              <legend className={styles.srOnly}>
                Настройки нового проекта
              </legend>

              <section className={styles.panel} aria-labelledby="basic-title">
                <h2 id="basic-title">Основное</h2>

                <label className={styles.field}>
                  <span>Название проекта</span>
                  <input
                    name="name"
                    type="text"
                    placeholder="Например, TPU.Metrics"
                    maxLength={255}
                    required
                  />
                </label>

                <label className={styles.field}>
                  <span>Ссылка на витрину проектов</span>
                  <input
                    name="showcaseUrl"
                    type="url"
                    placeholder="https://..."
                  />
                </label>

                <div className={styles.dates}>
                  <span className={styles.dateCaption}>Сроки проекта</span>

                  <label className={styles.dateField}>
                    <span>от</span>
                    <input
                      name="startDate"
                      type="date"
                      aria-label="Дата начала проекта"
                      value={startDate}
                      onChange={(event) => setStartDate(event.target.value)}
                    />
                  </label>

                  <label className={styles.dateField}>
                    <span>до</span>
                    <input
                      name="deadline"
                      type="date"
                      aria-label="Дата завершения проекта"
                      min={startDate || undefined}
                    />
                  </label>
                </div>
              </section>

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
                        placeholder="https://gitlab.com/group/project"
                        required
                      />
                    </label>

                    <label className={styles.field}>
                      <span>Токен</span>
                      <input
                        name="gitlabToken"
                        type="password"
                        placeholder="Введите токен"
                        autoComplete="off"
                        required
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
                        placeholder="https://redmine.../projects/..."
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
                className={styles.panel}
                aria-labelledby="statuses-title"
              >
                <h2 id="statuses-title">Спринты и статусы</h2>

                <div className={styles.settingRow}>
                  <label htmlFor="sprint-weeks">Длина спринта</label>

                  <div className={styles.numberField}>
                    <input
                      id="sprint-weeks"
                      name="sprintWeeks"
                      type="number"
                      min="1"
                      max="12"
                      step="1"
                      defaultValue="1"
                      required
                    />
                    <span>нед.</span>
                  </div>
                </div>

                <p className={styles.hint}>По умолчанию — 1 неделя</p>

                <h3 className={styles.subheading}>
                  Дни без активности в GitLab и Redmine
                </h3>

                <div className={styles.settingRow}>
                  <label className={styles.statusLabel} htmlFor="active-days">
                    <span
                      className={styles.dot}
                      data-color="green"
                      aria-hidden="true"
                    />
                    Идёт работа / Активен
                  </label>

                  <div className={styles.numberField}>
                    <span>до</span>
                    <input
                      id="active-days"
                      name="activeDays"
                      type="number"
                      min="0"
                      step="1"
                      defaultValue="3"
                      required
                    />
                    <span>дн.</span>
                  </div>
                </div>

                <div className={styles.settingRow}>
                  <label className={styles.statusLabel} htmlFor="warning-days">
                    <span
                      className={styles.dot}
                      data-color="yellow"
                      aria-hidden="true"
                    />
                    Замедление
                  </label>

                  <div className={styles.numberField}>
                    <span>до</span>
                    <input
                      id="warning-days"
                      name="warningDays"
                      type="number"
                      min="1"
                      step="1"
                      value={warningDays}
                      onChange={(event) => setWarningDays(event.target.value)}
                      required
                    />
                    <span>дн.</span>
                  </div>
                </div>

                <div className={styles.settingRow}>
                  <span className={styles.statusLabel}>
                    <span
                      className={styles.dot}
                      data-color="red"
                      aria-hidden="true"
                    />
                    Без активности
                  </span>

                  <span>более {warningDays || '—'} дн.</span>
                </div>
              </section>
            </fieldset>

            <aside className={styles.help} aria-labelledby="help-title">
              <h2 id="help-title">Как это работает</h2>

              <ol>
                <li>
                  Укажите название, ссылку на витрину проектов и сроки
                </li>
                <li>
                  Подключите GitLab и Redmine: ссылка и токен
                </li>
                <li>
                  Задайте длину спринта и дни для статусов
                </li>
                <li>
                  После создания добавьте студентов по почте в настройках
                  проекта
                </li>
              </ol>
            </aside>
          </div>

          {saveError && (
            <p className={styles.error} role="alert">
              {saveError}
            </p>
          )}

          <footer className={styles.actions}>
            <button
              className={styles.createButton}
              type="submit"
              disabled={saving}
            >
              {saving ? 'Создаём проект…' : 'Создать проект'}
            </button>

            <Link className={styles.cancelButton} to="/">
              Отмена
            </Link>
          </footer>
        </form>
      ) : (
        <div className={styles.result}>
          {loadingData ? (
            <ProjectLoadingCard name={createdProject.name} />
          ) : (
            <section className={styles.panel}>
              <h2>{createdProject.name}</h2>
              <p>Проект сохранён в базе данных.</p>

              {dataError && (
                <>
                  <p className={styles.error} role="alert">
                    Данные интеграций загрузить не удалось: {dataError}
                  </p>

                  <button
                    className={styles.cancelButton}
                    type="button"
                    onClick={() => void loadProjectData(createdProject.id)}
                  >
                    Повторить загрузку
                  </button>
                </>
              )}

              {liveCard && (
                <p>
                  Коммитов за последние 30 дней: {liveCard.summary.commits}
                </p>
              )}

              <div className={styles.resultActions}>
                <Link
                  className={styles.createButton}
                  to={`/projects/${createdProject.id}`}
                >
                  Открыть проект
                </Link>

                <Link className={styles.cancelButton} to="/">
                  К проектам
                </Link>
              </div>
            </section>
          )}
        </div>
      )}
    </section>
  )
}