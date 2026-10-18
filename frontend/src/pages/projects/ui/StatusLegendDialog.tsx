import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import styles from './StatusLegendDialog.module.css'

interface StatusLegendDialogProps {
  open: boolean
  onClose: () => void
}

type StatusColor = 'green' | 'yellow' | 'orange' | 'red' | 'gray'

interface StatusItem {
  color: StatusColor
  label: string
  description: string
}

const sourceStatuses: StatusItem[] = [
  {
    color: 'green',
    label: 'Зелёный',
    description: 'активность ≤ 3 дн. назад',
  },
  {
    color: 'yellow',
    label: 'Жёлтый',
    description: '4–7 дн. назад',
  },
  {
    color: 'red',
    label: 'Красный',
    description: 'более 7 дн. назад',
  },
]

const projectStatuses: StatusItem[] = [
  {
    color: 'green',
    label: 'Идёт работа',
    description: 'оба источника зелёные',
  },
  {
    color: 'yellow',
    label: 'Замедление',
    description: 'хотя бы один не зелёный',
  },
  {
    color: 'red',
    label: 'Простой',
    description: 'оба источника красные',
  },
  {
    color: 'gray',
    label: 'Загрузка данных',
    description: 'идёт импорт',
  },
]

const studentStatuses: StatusItem[] = [
  {
    color: 'green',
    label: 'Активен',
    description: 'оба источника зелёные',
  },
  {
    color: 'yellow',
    label: 'Частично',
    description: 'один зелёный, другой нет',
  },
  {
    color: 'orange',
    label: 'Замедление',
    description: 'нет зелёных, есть жёлтый',
  },
  {
    color: 'red',
    label: 'Простой',
    description: 'оба красные',
  },
  {
    color: 'gray',
    label: 'Нет данных',
    description: 'аккаунты не привязаны',
  },
]

function StatusList({
  items,
  className,
}: {
  items: StatusItem[]
  className: string
}) {
  return (
    <dl className={className}>
      {items.map(({ color, label, description }) => (
        <div key={label}>
          <dt>
            <span
              className={styles.statusDot}
              data-color={color}
              aria-hidden="true"
            />
            {label}
          </dt>
          <dd>{description}</dd>
        </div>
      ))}
    </dl>
  )
}

export function StatusLegendDialog({
  open,
  onClose,
}: StatusLegendDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

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
      id="status-legend"
      className={styles.statusDialog}
      aria-labelledby="status-dialog-title"
      onClose={onClose}
      onClick={(event) => {
        if (event.target !== event.currentTarget) return

        const bounds = event.currentTarget.getBoundingClientRect()

        const clickedOutside =
          event.clientX < bounds.left ||
          event.clientX > bounds.right ||
          event.clientY < bounds.top ||
          event.clientY > bounds.bottom

        if (clickedOutside) closeDialog()
      }}
    >
      <div className={styles.dialogHeader}>
        <h2 id="status-dialog-title">Шкала статусов</h2>

        <button
          type="button"
          className={styles.closeButton}
          aria-label="Закрыть шкалу статусов"
          onClick={closeDialog}
          autoFocus
        >
          <X size={22} aria-hidden="true" />
        </button>
      </div>

      <section
        className={styles.sourceSection}
        aria-labelledby="source-status-title"
      >
        <h3 id="source-status-title">
          Индикатор источника (GitLab, Redmine)
        </h3>

        <StatusList
          items={sourceStatuses}
          className={styles.sourceScale}
        />
      </section>

      <div className={styles.statusColumns}>
        <section aria-labelledby="project-status-title">
          <h3 id="project-status-title">Статус проекта</h3>

          <StatusList
            items={projectStatuses}
            className={styles.statusList}
          />
        </section>

        <section aria-labelledby="student-status-title">
          <h3 id="student-status-title">Статус студента</h3>

          <StatusList
            items={studentStatuses}
            className={styles.statusList}
          />
        </section>
      </div>

      <p className={styles.dialogNote}>
        Дни задаются отдельно для каждого проекта в его настройках.
      </p>
    </dialog>
  )
}