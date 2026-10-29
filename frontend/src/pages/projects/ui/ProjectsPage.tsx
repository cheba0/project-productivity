import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { Link } from 'react-router'

import {
  getProjects,
  type ProjectFilter,
  type ProjectListResponse,
} from '../../../entities/project'

import { ProjectDataCard } from './ProjectDataCard'
import styles from './ProjectsPage.module.css'

const filters: { value: ProjectFilter; label: string }[] = [
  { value: 'active', label: 'Активные' },
  { value: 'paused', label: 'На паузе' },
  { value: 'archived', label: 'Архив' },
]

export function ProjectsPage() {
  const [filter, setFilter] = useState<ProjectFilter>('active')
  const [result, setResult] = useState<ProjectListResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    getProjects(filter, controller.signal)
      .then((response) => {
        if (!controller.signal.aborted) {
          setResult(response)
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error
              ? reason.message
              : 'Не удалось загрузить проекты.',
          )
        }
      })

    return () => controller.abort()
  }, [filter, reload])

  function refresh() {
    setResult(null)
    setError(null)
    setReload((value) => value + 1)
  }

  function changeFilter(value: ProjectFilter) {
    if (value === filter) return

    setResult(null)
    setError(null)
    setFilter(value)
  }

  const loading = result === null && error === null

  return (
    <section aria-labelledby="projects-heading">
      <div className={styles.titleRow}>
        <div>
          <h1 id="projects-heading">Проекты</h1>
          <p className={styles.subtitle}>
            Прогресс, интеграции и сроки
          </p>
        </div>

        <div
          className={styles.filters}
          role="group"
          aria-label="Категория проектов"
        >
          {filters.map((item) => (
            <button
              key={item.value}
              type="button"
              className={
                filter === item.value ? styles.selected : styles.filter
              }
              aria-pressed={filter === item.value}
              onClick={() => changeFilter(item.value)}
            >
              {item.label} {result?.counts[item.value] ?? '…'}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <p className={styles.message} role="status">
          Загрузка списка проектов…
        </p>
      )}

      {error && (
        <div className={styles.message} role="alert">
          <p>{error}</p>
          <button className="button" type="button" onClick={refresh}>
            Повторить
          </button>
        </div>
      )}

      {result && (
        <>
          {result.items.length === 0 && (
            <p className={styles.message}>
              В этой категории пока нет проектов.
            </p>
          )}

          <div className={styles.grid}>
            {result.items.map((project) => (
              <ProjectDataCard key={project.id} project={project} />
            ))}

            {filter !== 'archived' && (
              <Link className={styles.newProject} to="/projects/new">
                <span className={styles.newProjectIcon}>
                  <Plus size={22} strokeWidth={1.5} aria-hidden="true" />
                </span>

                <span className={styles.newProjectTitle}>
                  Новый проект
                </span>

                <small>название · витрина · GitLab · Redmine</small>
              </Link>
            )}
          </div>
        </>
      )}
    </section>
  )
}