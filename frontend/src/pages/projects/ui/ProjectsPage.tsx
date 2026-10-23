import { useEffect, useState } from 'react'
import { Info, Plus, RefreshCw } from 'lucide-react'
import {
  getProjects,
  ProjectCard,
  type Project,
  type ProjectCategory,
} from '../../../entities/project'
import { demoProjects } from '../model/demoProjects'
import { StatusLegendDialog } from './StatusLegendDialog'
import { Link } from 'react-router'
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
  const [isStatusLegendOpen, setIsStatusLegendOpen] = useState(false)

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
          onClick={() => setIsStatusLegendOpen(true)}
        >
          <Info size={16} aria-hidden="true" />
          Шкала статусов
        </button>
      </div>
      <StatusLegendDialog
        open={isStatusLegendOpen}
        onClose={() => setIsStatusLegendOpen(false)}
      />
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
              <Link className={styles.newProject} to="/projects/new">
                <Plus size={34} strokeWidth={1.5} aria-hidden="true" />
                <span>Новый проект</span>
                <small>Название · витрина · GitLab · Redmine</small>
              </Link>
            )}
          </div>
        </>
      )}
    </section>
  )
}
