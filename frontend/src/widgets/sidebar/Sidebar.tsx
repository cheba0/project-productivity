import styles from './Sidebar.module.css'

export function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <nav aria-label="Основная навигация">
        <a
          href="/"
          className={styles.active}
          aria-label="Проекты"
          aria-current="page"
          title="Проекты"
        >
        </a>
      </nav>
      <div className={styles.bottom}>
        <button
          className="icon-button"
          disabled
          aria-label="Настройки: пока недоступны"
          title="Настройки — позже"
        >
        </button>
        <button
          className="icon-button"
          disabled
          aria-label="Помощь: пока недоступна"
          title="Помощь — позже"
        >
        </button>
      </div>
    </aside>
  )
}
