import {useEffect, useState} from 'react'
import {LayoutGrid, Info, LogOut, Settings, LoaderCircle} from 'lucide-react'
import {Link, useLocation, useMatch} from 'react-router'

import {getProjects, type ProjectListResponse} from '../../entities/project'
import {useAuthStore} from '../../store/authStore'
import {useProjectSyncStore} from '../../store/projectSyncStore'
import {CurrentSprint} from './CurrentSprint'
import {DataSources} from './DataSources'

import styles from './Sidebar.module.css'

interface SidebarProps {
  userName?: string
  loggingOut?: boolean
  onLogout: () => void
  onOpenStatusLegend: () => void
  onOpenSettings: () => void
}

interface ProjectsResult {
  key: string
  data: ProjectListResponse | null
  error: string | null
}

function getInitials(name: string): string {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

export function Sidebar({
  userName, loggingOut = false, onLogout, onOpenStatusLegend, onOpenSettings,
}: SidebarProps) {
  const {pathname} = useLocation()
  const projectMatch = useMatch('/projects/:projectId/*')

  const user = useAuthStore((state) => state.user)
  const email = user?.email

  const syncRevision = useProjectSyncStore((state) => state.revision)

  const [projectsResult, setProjectsResult] = useState<ProjectsResult | null>(null)

  const requestKey = JSON.stringify([email, pathname, syncRevision])
  const currentResult = projectsResult?.key === requestKey ? projectsResult : null

  const isHome = pathname === '/'
  const isCreatePage = pathname === '/projects/new'
  const currentProjectId = isCreatePage ? undefined : projectMatch?.params.projectId
  const isProjectsSection = isHome || pathname.startsWith('/projects/')

  const displayName =
    [user?.first_name, user?.last_name].filter(Boolean).join(' ') || userName || email || ''

  useEffect(() => {
    if (!email) return

    const controller = new AbortController()

    getProjects('active', controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return
        setProjectsResult({key: requestKey, data, error: null})
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return

        setProjectsResult({
          key: requestKey,
          data: null,
          error: reason instanceof Error ? reason.message : 'Не удалось загрузить проекты.',
        })
      })

    return () => controller.abort()
  }, [email, requestKey])

  return (
    <aside className={styles.sidebar}>
      <Link className={styles.brand} to="/">
        <span className={styles.logo} aria-hidden="true">
          <span /><span /><span /><span />
        </span>
        <span>ТПУ.Метрика</span>
      </Link>

      <nav className={styles.navigation} aria-label="Основная навигация">
        <p className={styles.caption}>Меню</p>

        <Link
          className={`${styles.navLink} ${isProjectsSection ? styles.active : ''}`}
          to="/" aria-current={pathname === '/' ? 'page' : undefined}
        >
          <LayoutGrid size={23} aria-hidden="true" />
          <span>Проекты</span>

          {email && (
            <span className="ml-auto flex items-center text-xs text-[#58655e]">
              {!currentResult ? (
                <span role="status" aria-label="Загрузка количества проектов">
                  <LoaderCircle size={14} className="animate-spin" aria-hidden="true" />
                </span>
              ) : currentResult.data ? (
                <span aria-label={`Активных проектов: ${currentResult.data.counts.active}`}>
                  {currentResult.data.counts.active}
                </span>
              ) : (
                <span title={currentResult.error ?? 'Не удалось загрузить количество проектов'} aria-label="Ошибка загрузки">
                  !
                </span>
              )}
            </span>
          )}
        </Link>
      </nav>

      <DataSources disabled={loggingOut} />

      <div className={styles.bottom}>

        {email && currentProjectId && (
          <CurrentSprint key={currentProjectId} projectId={currentProjectId} refreshKey={pathname} />
        )}

        <button className={styles.action} type="button" onClick={onOpenStatusLegend}>
          <Info size={18} aria-hidden="true" />
          Шкала статусов
        </button>

        <button className={styles.action} type="button" onClick={onOpenSettings} aria-haspopup="dialog">
          <Settings size={18} aria-hidden="true" />
          Настройки
        </button>

        <button
          className={styles.action} type="button"
          disabled={loggingOut || !email} onClick={onLogout}
        >
          <LogOut size={18} aria-hidden="true" />
          {loggingOut ? 'Выходим…' : 'Выйти'}
        </button>

        {displayName && (
          <div className={styles.profile}>
            <span className={styles.avatar} aria-hidden="true">{getInitials(displayName)}</span>

            <div className={styles.profileText}>
              <strong>{displayName}</strong>
              <span>Пользователь</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}