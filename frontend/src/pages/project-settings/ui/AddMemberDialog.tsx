import { useEffect, useId, useRef } from 'react'
import { X } from 'lucide-react'

import styles from './AddMemberDialog.module.css'

type AddMemberDialogProps = {
  open: boolean
  onClose: () => void
}

export function AddMemberDialog({
  open,
  onClose,
}: AddMemberDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const formRef = useRef<HTMLFormElement>(null)
  const titleId = useId()
  const descriptionId = useId()

  useEffect(() => {
    const dialog = dialogRef.current

    if (!dialog) return

    if (open && !dialog.open) {
      formRef.current?.reset()
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
      aria-describedby={descriptionId}
      onClose={onClose}
      onClick={(event) => {
        if (event.target !== event.currentTarget) return

        const rect = event.currentTarget.getBoundingClientRect()

        const clickedOutside =
          event.clientX < rect.left ||
          event.clientX > rect.right ||
          event.clientY < rect.top ||
          event.clientY > rect.bottom

        if (clickedOutside) {
          closeDialog()
        }
      }}
    >
      <header className={styles.header}>
        <h2 id={titleId}>Добавить участника</h2>

        <button
          className={styles.closeButton}
          type="button"
          onClick={closeDialog}
          aria-label="Закрыть окно"
        >
          <X size={20} aria-hidden="true" />
        </button>
      </header>

      <form
        ref={formRef}
        className={styles.form}
        onSubmit={(event) => event.preventDefault()}
      >
        <label className={styles.field}>
          <span>Почта студента</span>
          <input
            name="email"
            type="email"
            placeholder="student@tpu.ru"
            autoComplete="off"
            autoFocus
          />
        </label>

        <label className={styles.field}>
          <span>Роль</span>
          <input
            name="role"
            type="text"
            placeholder="Например, Frontend-разработчик"
          />
        </label>

        <p id={descriptionId} className={styles.hint}>
          Ссылки и токены на GitLab и Redmine студент добавит сам
          в своём профиле.
        </p>

        <footer className={styles.actions}>
          <button
            className={styles.addButton}
            type="button"
            disabled
            title="Добавление участника пока не подключено"
          >
            Добавить
          </button>

          <button
            className={styles.cancelButton}
            type="button"
            onClick={closeDialog}
          >
            Отмена
          </button>
        </footer>
      </form>
    </dialog>
  )
}