import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { Link, useMatch } from 'react-router'
import { useProjectHeaderStore } from '../../store/projectHeaderStore'
import { getProject } from '../../entities/project'

import styles from './Header.module.css'

export function Header() {
  const createMatch = useMatch('/projects/new')
  const settingsMatch = useMatch('/projects/:projectId/settings')
  const projectMatch = useMatch('/projects/:projectId')

  const isCreatePage = Boolean(createMatch)
  const isSettingsPage = Boolean(settingsMatch)
  const showSprintControls = Boolean(projectMatch) && !isCreatePage

  const setControlsElement = useProjectHeaderStore((state) => state.setControlsElement)

  const projectId = isCreatePage
    ? undefined
    : settingsMatch?.params.projectId ??
      projectMatch?.params.projectId

  const [loadedProject, setLoadedProject] = useState<{
    id: string
    name: string
  } | null>(null)

  useEffect(() => {
    if (!projectId) return

    const controller = new AbortController()

    getProject(projectId, controller.signal)
      .then((project) => {
        if (!controller.signal.aborted) {
          setLoadedProject({
            id: project.id,
            name: project.name,
          })
        }
      })
      .catch(() => {
        // Ошибку загрузки показывает сама страница проекта.
        if (!controller.signal.aborted) {
          setLoadedProject(null)
        }
      })

    return () => controller.abort()
  }, [projectId])

  const projectName = loadedProject !== null && loadedProject?.id === projectId ? loadedProject.name: 'Проект'

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        {isCreatePage || projectId ? (
          <nav
            className={styles.breadcrumbs}
            aria-label="Навигационная цепочка"
          >
            <Link to="/">Проекты</Link>
            <span aria-hidden="true">›</span>

            {isCreatePage ? (
              <span aria-current="page">Новый проект</span>
            ) : isSettingsPage ? (
              <>
                <Link to={`/projects/${projectId}`}>
                  {projectName}
                </Link>

                <span aria-hidden="true">›</span>
                <span aria-current="page">Настройки</span>
              </>
            ) : (
              <span aria-current="page">{projectName}</span>
            )}
          </nav>
        ) : (
          <span className={styles.title}>Проекты</span>
        )}
      </div>

      <div className={styles.right}>
        {showSprintControls ? (
          <div
            className={styles.projectControls}
            ref={setControlsElement}
          />
        ) : (
          <label className={styles.search}>
            <Search size={17} aria-hidden="true" />

            <input
              type="search"
              placeholder="Поиск по проектам и студентам…"
              aria-label="Поиск по проектам и студентам"
              disabled
              title="Поиск пока не подключён"
            />
          </label>
        )}
      </div>
    </header>
  )
}