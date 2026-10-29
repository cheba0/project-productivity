import { useEffect, useId, useRef, useState } from 'react'
import { X } from 'lucide-react'

import styles from './SettingsDialog.module.css'

interface SettingsDialogProps {
  open: boolean
  onClose: () => void
}

type Theme = 'light' | 'dark' | 'system'

const themes: { value: Theme; label: string }[] = [
  { value: 'light', label: 'Светлая' },
  { value: 'dark', label: 'Тёмная' },
  { value: 'system', label: 'Системная' },
]

export function SettingsDialog({
  open,
  onClose,
}: SettingsDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const themeHintId = useId()

  const [theme, setTheme] = useState<Theme>('light')

  useEffect(() => {
    const dialog = dialogRef.current

    if (!dialog) return

    if (open && !dialog.open) {
      dialog.showModal()
    } else if (!open && dialog.open) {
      dialog.close()
    }
  }, [open])

  function closeDialog() {
    dialogRef.current?.close()
  }

  return (
    <dialog
      ref={dialogRef}
      className={styles.dialog}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(event) => {
        if (event.target !== event.currentTarget) return

        const rect = event.currentTarget.getBoundingClientRect()

        const clickedOutside =
          event.clientX < rect.left ||
          event.clientX > rect.right ||
          event.clientY < rect.top ||
          event.clientY > rect.bottom

        if (clickedOutside) closeDialog()
      }}
    >
      <header className={styles.header}>
        <h2 id={titleId}>Настройки</h2>

        <button
          className={styles.closeButton}
          type="button"
          onClick={closeDialog}
          aria-label="Закрыть настройки"
          autoFocus
        >
          <X size={22} aria-hidden="true" />
        </button>
      </header>

      <section className={styles.notifications}>
        <h3>Оповещения</h3>
        <p>
          Эта возможность находится в разработке и появится позже
        </p>
      </section>

      <section className={styles.appearance}>
        <div className={styles.appearanceHeading}>
          <h3>Внешний вид</h3>
          <p>Тема интерфейса</p>
        </div>

        <div
          className={styles.themes}
          role="group"
          aria-label="Тема интерфейса"
          aria-describedby={themeHintId}
        >
          {themes.map((item) => (
            <button
              key={item.value}
              className={
                theme === item.value
                  ? styles.selectedTheme
                  : styles.themeButton
              }
              type="button"
              aria-pressed={theme === item.value}
              onClick={() => setTheme(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      <footer className={styles.footer}>
        <button
          className={styles.doneButton}
          type="button"
          onClick={closeDialog}
        >
          Готово
        </button>
      </footer>
    </dialog>
  )
}