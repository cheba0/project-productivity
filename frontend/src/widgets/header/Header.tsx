import type { ReactNode } from 'react'
import { Link, useMatch } from 'react-router'

import styles from './Header.module.css'

export function Header({ actions }: { actions?: ReactNode }) {
  const isProjectCreatePage = Boolean(useMatch('/projects/new'))
  const isProjectSettingsPage = Boolean(useMatch('/projects/:projectId/settings'))
  const showBackButton = isProjectCreatePage || isProjectSettingsPage

  return (
    <header className={styles.header}>
      <div className={styles.brandGroup}>
        <Link className={styles.brand} to="/">
          TPU.Metrics
        </Link>

        {showBackButton  && (
          <Link className={styles.backButton} to="/">
            &lt; Проекты
          </Link>
        )}
      </div>

      <div className={styles.actions}>
        <span className={styles.integrations}>
          GitLab + Redmine
        </span>

        {actions}
      </div>
    </header>
  )
}