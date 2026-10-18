import { useEffect, useId, useRef, useState } from 'react'
import { X } from 'lucide-react'

import styles from './DeleteProjectDialog.module.css'

type DeleteProjectDialogProps = {
  open: boolean
  projectName: string
  onClose: () => void
}

export function DeleteProjectDialog({
  open,
  projectName,
  onClose,
}: DeleteProjectDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [confirmation, setConfirmation] = useState('')

  const titleId = useId()
  const descriptionId = useId()

  const isConfirmed =
    projectName.length > 0 && confirmation === projectName

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

  function handleClose() {
    setConfirmation('')
    onClose()
  }

  return (
    <dialog
      ref={dialogRef}
      className={styles.dialog}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      onClose={handleClose}
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
        <h2 id={titleId}>Удалить проект?</h2>

        <button
          className={styles.closeButton}
          type="button"
          onClick={closeDialog}
          aria-label="Закрыть окно"
        >
          <X size={20} aria-hidden="true" />
        </button>
      </header>

      <p id={descriptionId} className={styles.description}>
        Проект «{projectName}» и все его данные будут удалены
        без возможности восстановления.
      </p>

      <form
        className={styles.form}
        onSubmit={(event) => event.preventDefault()}
      >
        <label className={styles.field}>
          <span>Для подтверждения введите название проекта</span>

          <input
            name="projectNameConfirmation"
            type="text"
            placeholder="Название проекта"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            autoComplete="off"
            spellCheck={false}
            autoFocus
          />
        </label>

        <footer className={styles.actions}>
          <button
            className={styles.deleteButton}
            type="button"
            disabled={!isConfirmed}
            title={
              isConfirmed
                ? 'Удаление пока не подключено'
                : 'Введите точное название проекта'
            }
          >
            Удалить проект
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