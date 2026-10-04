import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'


function App() {
  const user = useAuthStore((state) => state.user)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isLoading = useAuthStore((state) => state.isLoading)
  const login = useAuthStore((state) => state.login)
  const checkAuth = useAuthStore((state) => state.checkAuth)
  const logout = useAuthStore((state) => state.logout)

  useEffect(() => {checkAuth()}, [checkAuth])

  if (isLoading) {return <div>Загрузка...</div>}


  return (
    <div>
      <h1>Наше приложение</h1>

      {isAuthenticated && user ? (
        <div>
          <h2>
            Привет, {user.first_name}!
          </h2>

          <p>
            Email: {user.email}
          </p>

          <button onClick={logout}>
            Выйти
          </button>
        </div>
      ) : (
        <button onClick={login}>
          Войти
        </button>
      )}
    </div>
  )
}


export default App