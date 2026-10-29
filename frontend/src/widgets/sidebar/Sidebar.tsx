import {
  LayoutGrid,
  Info,
  LogOut,
  Settings,
} from 'lucide-react'
import { Link, useLocation } from 'react-router'

import styles from './Sidebar.module.css'

interface SidebarProps {
  userName?: string
  loggingOut?: boolean
  onLogout: () => void
  onOpenStatusLegend: () => void
  onOpenSettings: () => void
}

function getInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

export function Sidebar({
  userName,
  loggingOut = false,
  onLogout,
  onOpenStatusLegend,
  onOpenSettings,
}: SidebarProps) {
  const { pathname } = useLocation()

  const isProjectsSection =
    pathname === '/' || pathname.startsWith('/projects/')

  return (
    <aside className={styles.sidebar}>
      <Link className={styles.brand} to="/">
        <span className={styles.logo} aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </span>

        <span>ТПУ.Метрика</span>
      </Link>

      <nav className={styles.navigation} aria-label="Основная навигация">
        <p className={styles.caption}>Меню</p>

        <Link
          className={`${styles.navLink} ${
            isProjectsSection ? styles.active : ''
          }`}
          to="/"
          aria-current={pathname === '/' ? 'page' : undefined}
        >
          <LayoutGrid size={23} aria-hidden="true" />
          <span>Проекты</span>
        </Link>
      </nav>

      <div className={styles.bottom}>
        <button
          className={styles.action}
          type="button"
          onClick={onOpenStatusLegend}
        >
          <Info size={18} aria-hidden="true" />
          Шкала статусов
        </button>

        <button
          className={styles.action}
          type="button"
          onClick={onOpenSettings}
          aria-haspopup="dialog"
        >
          <Settings size={18} aria-hidden="true" />
          Настройки
        </button>

        <button
          className={styles.action}
          type="button"
          disabled={loggingOut || !userName}
          onClick={onLogout}
        >
          <LogOut size={18} aria-hidden="true" />
          {loggingOut ? 'Выходим…' : 'Выйти'}
        </button>

        {userName && (
          <div className={styles.profile}>
            <span className={styles.avatar} aria-hidden="true">
              {getInitials(userName)}
            </span>

            <div className={styles.profileText}>
              <strong>{userName}</strong>
              <span>Пользователь</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}