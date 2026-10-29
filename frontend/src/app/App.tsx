import {
  useEffect,
  useState,
  type PropsWithChildren,
} from 'react'
import { Header } from '../widgets/header'
import { Sidebar } from '../widgets/sidebar'
import { AppRoutes } from './router/AppRoutes'
import styles from './App.module.css'
import { useAuthStore } from '../store/authStore'
import { StatusLegendDialog } from '../widgets/status-legend'
import { SettingsDialog } from '../widgets/settings-dialog'

type AppLayoutProps = PropsWithChildren<{
  userName?: string
  loggingOut: boolean
  onLogout: () => void
}>

function AppLayout({
  children,
  userName,
  loggingOut,
  onLogout,
}: AppLayoutProps) {
  const [isStatusLegendOpen, setIsStatusLegendOpen] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  return (
    <div className={styles.layout}>
      <Sidebar
        userName={userName}
        loggingOut={loggingOut}
        onLogout={onLogout}
        onOpenStatusLegend={() => setIsStatusLegendOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      <div className={styles.body}>
        <Header />

        <main id="main-content" className={styles.content}>
          {children}
        </main>
      </div>

      <StatusLegendDialog
        open={isStatusLegendOpen}
        onClose={() => setIsStatusLegendOpen(false)}
      />
      <SettingsDialog
        open={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  )
}

export default function App() {
  const { user, isLoading, error, checkAuth, logout } = useAuthStore()

  const [logoutError, setLogoutError] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)

  useEffect(() => {
    void checkAuth()
  }, [checkAuth])

  async function handleLogout() {
    setLoggingOut(true)
    setLogoutError(false)

    try {
      await logout()
    } catch {
      setLogoutError(true)
    } finally {
      setLoggingOut(false)
    }
  }

  function retryAuth() {
    const url = new URL(window.location.href)

    url.searchParams.delete('auth_error')
    window.history.replaceState(null, '', url.toString())

    void checkAuth()
  }

  return (
    <>
      <a className="skip-link" href="#main-content">
        К содержимому
      </a>

      <AppLayout
        userName={user?.first_name}
        loggingOut={loggingOut}
        onLogout={() => void handleLogout()}
      >
        {isLoading ? (
          <p role="status">Проверяем сессию и выполняем вход…</p>
        ) : error ? (
          <div role="alert">
            <p>{error}</p>

            <button
              type="button"
              className="button"
              onClick={retryAuth}
            >
              Повторить
            </button>
          </div>
        ) : user ? (
          <>
            {logoutError && (
              <p role="alert">
                Не удалось выйти. Попробуйте ещё раз.
              </p>
            )}

            <AppRoutes />
          </>
        ) : (
          <div>
            <p>Вы вышли из приложения.</p>

            <button
              type="button"
              className="button"
              onClick={() => window.location.reload()}
            >
              Продолжить
            </button>
          </div>
        )}
      </AppLayout>
    </>
  )
}