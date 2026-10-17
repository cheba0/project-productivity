import type { ReactNode } from 'react'
import styles from './Header.module.css'

export function Header({ actions }: { actions?: ReactNode }) {
  return (
    <header className={styles.header}>
      <a className={styles.brand} href="/">
        TPU.Metrics
      </a>
      <div className={styles.actions}>
        <span className={styles.integrations}>
          GitLab + Redmine
        </span>
        {actions}
      </div>
    </header>
  )
}
