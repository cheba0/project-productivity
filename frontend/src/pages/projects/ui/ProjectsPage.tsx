import { useEffect, useRef, useState } from 'react'
import { Info, Plus, RefreshCw, X } from 'lucide-react'
import {
  activityLabels,
  getProjects,
  ProjectCard,
  type Project,
  type ProjectCategory,
} from '../../../entities/project'
import { demoProjects } from '../model/demoProjects'
import styles from './ProjectsPage.module.css'

const categories: { value: ProjectCategory; label: string }[] = [
  { value: 'active', label: 'Активные' },
  { value: 'paused', label: 'На паузе' },
  { value: 'archived', label: 'Архив' },
]

export function ProjectsPage() {
  const [source, setSource] = useState<'demo' | 'api'>('demo')
  const [category, setCategory] = useState<ProjectCategory>('active')
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)
  const statusDialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    if (source !== 'api') return
    const controller = new AbortController()
    getProjects(controller.signal)
      .then(setProjects)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted)
          setError(
            reason instanceof Error
              ? reason.message
              : 'Ошибка загрузки проектов',
          )
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [source, reload])

  function loadApi() {
    setLoading(true)
    setError(null)
    setSource('api')
    setReload((value) => value + 1)
  }

  const visibleProjects =
    source === 'demo'
      ? demoProjects.filter((project) => project.category === category)
      : projects

  return (
    <section aria-labelledby="projects-heading">
      <div className={styles.titleRow}>
        <div>
          <h1 id="projects-heading">Проекты</h1>
          <p className={styles.subtitle}>Прогресс, интеграции и сроки</p>
        </div>
        <label className={styles.source}>
          Источник данных
          <select
            value={source}
            onChange={(event) =>
              event.target.value === 'api' ? loadApi() : setSource('demo')
            }
          >
            <option value="demo">Макет</option>
            <option value="api">Данные API</option>
          </select>
        </label>
      </div>
      <div className={styles.toolbar}>
        {source === 'demo' ? (
          <div
            className={styles.filters}
            role="group"
            aria-label="Категория проектов"
          >
            {categories.map(({ value, label }) => (
              <button
                key={value}
                className={category === value ? styles.selected : styles.filter}
                aria-pressed={category === value}
                onClick={() => setCategory(value)}
              >
                {label} ·{' '}
                {
                  demoProjects.filter((project) => project.category === value)
                    .length
                }
              </button>
            ))}
          </div>
        ) : (
          <button className="button" disabled={loading} onClick={loadApi}>
            <RefreshCw size={16} /> Обновить
          </button>
        )}
        <button
          type="button"
          className="button"
          aria-haspopup="dialog"
          aria-controls="status-legend"
          onClick={() => statusDialogRef.current?.showModal()}
        >
          <Info size={16} aria-hidden="true" />
          Шкала статусов
        </button>
      </div>
      <dialog
        ref={statusDialogRef}
        id="status-legend"
        className={styles.statusDialog}
        aria-labelledby="status-dialog-title"
        onClick={(event) => {
          if (event.target !== event.currentTarget) return

          const bounds = event.currentTarget.getBoundingClientRect()

          const clickedOutside =
            event.clientX < bounds.left ||
            event.clientX > bounds.right ||
            event.clientY < bounds.top ||
            event.clientY > bounds.bottom

          if (clickedOutside) {
            event.currentTarget.close()
          }
        }}
      >
        <div className={styles.dialogHeader}>
          <h2 id="status-dialog-title">Шкала статусов</h2>

          <button
            type="button"
            className={styles.closeButton}
            aria-label="Закрыть шкалу статусов"
            onClick={() => statusDialogRef.current?.close()}
            autoFocus
          >
            <X size={22} aria-hidden="true" />
          </button>
        </div>

        <section
          className={styles.sourceSection}
          aria-labelledby="source-status-title"
        >
          <h3 id="source-status-title">
            Индикатор источника (GitLab, Redmine)
          </h3>

          <dl className={styles.sourceScale}>
            <div>
              <dt>
                <span
                  className={styles.statusDot}
                  data-color="green"
                  aria-hidden="true"
                />
                Зелёный
              </dt>
              <dd>активность ≤ 3 дн. назад</dd>
            </div>

            <div>
              <dt>
                <span
                  className={styles.statusDot}
                  data-color="yellow"
                  aria-hidden="true"
                />
                Жёлтый
              </dt>
              <dd>4–7 дн. назад</dd>
            </div>

            <div>
              <dt>
                <span
                  className={styles.statusDot}
                  data-color="red"
                  aria-hidden="true"
                />
                Красный
              </dt>
              <dd>более 7 дн. назад</dd>
            </div>
          </dl>
        </section>

        <div className={styles.statusColumns}>
          <section aria-labelledby="project-status-title">
            <h3 id="project-status-title">Статус проекта</h3>

            <dl className={styles.statusList}>
              <div>
                <dt>
                  <span
                    className={styles.statusDot}
                    data-color="green"
                    aria-hidden="true"
                  />
                  Идёт работа
                </dt>
                <dd>оба источника зелёные</dd>
              </div>

              <div>
                <dt>
                  <span
                    className={styles.statusDot}
                    data-color="yellow"
                    aria-hidden="true"
                  />
                  Замедление
                </dt>
                <dd>хотя бы один не зелёный</dd>
              </div>

              <div>
                <dt>
                  <span
                    className={styles.statusDot}
                    data-color="red"
                    aria-hidden="true"
                  />
                  Простой
                </dt>
                <dd>оба источника красные</dd>
              </div>

              <div>
                <dt>
                  <span
                    className={styles.statusDot}
                    data-color="gray"
                    aria-hidden="true"
                  />
                  Загрузка данных
                </dt>
                <dd>идёт импорт</dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="student-status-title">
            <h3 id="student-status-title">Статус студента</h3>

            <dl className={styles.statusList}>
              <div>
                <dt>
                  <span
                    className={styles.statusDot}
                    data-color="green"
                    aria-hidden="true"
                  />
                  Активен
                </dt>
                <dd>оба источника зелёные</dd>
              </div>

              <div>
                <dt>
                  <span
                    className={styles.statusDot}
                    data-color="yellow"
                    aria-hidden="true"
                  />
                  Частично
                </dt>
                <dd>один зелёный, другой нет</dd>
              </div>

              <div>
                <dt>
                  <span
                    className={styles.statusDot}
                    data-color="orange"
                    aria-hidden="true"
                  />
                  Замедление
                </dt>
                <dd>нет зелёных, есть жёлтый</dd>
              </div>

              <div>
                <dt>
                  <span
                    className={styles.statusDot}
                    data-color="red"
                    aria-hidden="true"
                  />
                  Простой
                </dt>
                <dd>оба красные</dd>
              </div>

              <div>
                <dt>
                  <span
                    className={styles.statusDot}
                    data-color="gray"
                    aria-hidden="true"
                  />
                  Нет данных
                </dt>
                <dd>аккаунты не привязаны</dd>
              </div>
            </dl>
          </section>
        </div>

        <p className={styles.dialogNote}>
          Дни задаются отдельно для каждого проекта в его настройках.
        </p>
      </dialog>
      {source === 'api' && loading ? (
        <p role="status" className={styles.message}>
          Загрузка проектов…
        </p>
      ) : source === 'api' && error ? (
        <p role="alert" className={styles.message}>
          {error}. Проверьте Analytics Service на порту 8003 и повторите запрос.
        </p>
      ) : (
        <>
          {visibleProjects.length === 0 && (
            <p className={styles.message}>Проектов пока нет.</p>
          )}
          <div className={styles.grid}>
            {visibleProjects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
            {(source === 'api' || category !== 'archived') && (
              <button
                className={styles.newProject}
                disabled
                title="Создание проектов — следующий этап"
              >
                <Plus size={34} strokeWidth={1.5} aria-hidden="true" />
                <span>Новый проект</span>
                <small>Название · витрина · GitLab · Redmine</small>
                <small>Создание пока недоступно</small>
              </button>
            )}
          </div>
        </>
      )}
    </section>
  )
}
