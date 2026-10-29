import { Search } from 'lucide-react'
import { Link, useMatch } from 'react-router'

import styles from './Header.module.css'

export function Header() {
  const isCreatePage = Boolean(useMatch('/projects/new'))
  const isSettingsPage = Boolean(
    useMatch('/projects/:projectId/settings'),
  )
  const isProjectPage = Boolean(useMatch('/projects/:projectId'))

  const showBackButton =
    isCreatePage || isSettingsPage || isProjectPage

  const title = isCreatePage
    ? 'Новый проект'
    : isSettingsPage
      ? 'Настройки проекта'
      : isProjectPage
        ? 'Проект'
        : 'Проекты'

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        {isCreatePage ? (
          <nav className={styles.breadcrumbs} aria-label="Навигационная цепочка">
            <Link to="/">Проекты</Link>
            <span aria-hidden="true">›</span>
            <span aria-current="page">Новый проект</span>
          </nav>
        ) : (
          <>
            <span className={styles.title}>{title}</span>

            {showBackButton && (
              <Link className={styles.backButton} to="/">
                <span aria-hidden="true">‹</span>
                Проекты
              </Link>
            )}
          </>
        )}
      </div>

      <div className={styles.right}>

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
      </div>
    </header>
  )
}