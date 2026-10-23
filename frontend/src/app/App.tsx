import {
  useEffect,
  useState,
  type PropsWithChildren,
  type ReactNode,
} from 'react'
import { Header } from '../widgets/header'
import { Sidebar } from '../widgets/sidebar'
import { AppRoutes } from './router/AppRoutes'
import styles from './App.module.css'
import { useAuthStore } from '../store/authStore'

function AppLayout({
  children,
  actions,
}: PropsWithChildren<{ actions: ReactNode }>) {
  return (
    <div className={styles.layout}>
      <Sidebar />
      <div className={styles.body}>
        <Header actions={actions} />
        <main id="main-content" className={styles.content}>
          {children}
        </main>
      </div>
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

  const actions = user ? (
    <>
      <span>{user.first_name}</span>

      <button
        type="button"
        className="button"
        disabled={loggingOut}
        onClick={handleLogout}
      >
        {loggingOut ? 'Выходим…' : 'Выйти'}
      </button>
    </>
  ) : null

  return (
    <>
      <a className="skip-link" href="#main-content">
        К содержимому
      </a>

      <AppLayout actions={actions}>
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