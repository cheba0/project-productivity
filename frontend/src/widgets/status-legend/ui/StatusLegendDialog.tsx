import { useEffect, useId, useRef } from 'react'
import { X } from 'lucide-react'

import styles from './StatusLegendDialog.module.css'

interface StatusLegendDialogProps {
  open: boolean
  onClose: () => void
}

type IndicatorColor = 'green' | 'yellow' | 'orange' | 'red' | 'gray'

function Dot({ color }: { color: IndicatorColor }) {
  return (
    <span
      className={styles.dot}
      data-color={color}
      aria-hidden="true"
    />
  )
}

function SourceBadge({
  name,
  colors,
}: {
  name: string
  colors: IndicatorColor[]
}) {
  const labels: Record<IndicatorColor, string> = {
    green: 'активно',
    yellow: 'замедление',
    orange: 'снижение активности',
    red: 'критично',
    gray: 'нет данных',
  }

  return (
    <span className={styles.sourceBadge}>
      {name}

      <span className={styles.sourceColors} aria-hidden="true">
        {colors.map((color, index) => (
          <span className={styles.colorOption} key={color}>
            {index > 0 && <span>/</span>}
            <Dot color={color} />
          </span>
        ))}
      </span>

      <span className={styles.srOnly}>
        : {colors.map((color) => labels[color]).join(' или ')}
      </span>
    </span>
  )
}

export function StatusLegendDialog({
  open,
  onClose,
}: StatusLegendDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const descriptionId = useId()

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

        if (clickedOutside) closeDialog()
      }}
    >
      <header className={styles.header}>
        <h2 id={titleId}>Шкала статусов</h2>

        <button
          className={styles.closeButton}
          type="button"
          onClick={closeDialog}
          aria-label="Закрыть шкалу статусов"
          autoFocus
        >
          <X size={20} aria-hidden="true" />
        </button>
      </header>

      <p id={descriptionId} className={styles.description}>
        Индикатор автоматического расчёта активности на основе данных
        из GitLab и Redmine
      </p>

      <div className={styles.thresholds}>
        <div className={styles.threshold} data-color="green">
          <Dot color="green" />
          <span><strong>Активно:</strong> до 3 дней назад</span>
        </div>

        <div className={styles.threshold} data-color="yellow">
          <Dot color="yellow" />
          <span><strong>Замедление:</strong> 4–7 дней назад</span>
        </div>

        <div className={styles.threshold} data-color="red">
          <Dot color="red" />
          <span><strong>Критично:</strong> более 7 дней назад</span>
        </div>
      </div>

      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <caption className={styles.srOnly}>
            Соответствие активности источников статусу проекта или студента
          </caption>

          <thead>
            <tr>
              <th scope="col">Статус (проект / студент)</th>
              <th scope="col">Состояние источников</th>
              <th scope="col">Интерпретация</th>
            </tr>
          </thead>

          <tbody>
            <tr>
              <th scope="row">
                <span className={styles.status}>
                  <Dot color="green" />
                  Идёт работа / Активен
                </span>
              </th>

              <td>
                <div className={styles.sources}>
                  <SourceBadge name="Redmine" colors={['green']} />
                  <span className={styles.separator}>+</span>
                  <SourceBadge name="GitLab" colors={['green']} />
                </div>
              </td>

              <td>Максимальная продуктивность</td>
            </tr>

            <tr>
              <th scope="row">
                <span className={styles.status}>
                  <Dot color="yellow" />
                  Частично
                </span>
              </th>

              <td>
                <div className={styles.sources}>
                  <SourceBadge name="Redmine" colors={['green']} />
                  <span className={styles.separator}>+</span>
                  <SourceBadge name="GitLab" colors={['yellow', 'red']} />
                  <span className={styles.note}>(или наоборот)</span>
                </div>
              </td>

              <td>Дисбаланс активности</td>
            </tr>

            <tr>
              <th scope="row">
                <span className={styles.status}>
                  <Dot color="orange" />
                  Замедление
                </span>
              </th>

              <td>
                <div className={styles.sources}>
                  <SourceBadge name="Redmine" colors={['yellow']} />
                  <span className={styles.separator}>+</span>
                  <SourceBadge name="GitLab" colors={['yellow', 'red']} />
                  <span className={styles.note}>(или наоборот)</span>
                </div>
              </td>

              <td>Общий спад темпа</td>
            </tr>

            <tr>
              <th scope="row">
                <span className={styles.status}>
                  <Dot color="red" />
                  Без активности
                </span>
              </th>

              <td>
                <div className={styles.sources}>
                  <SourceBadge name="Redmine" colors={['red']} />
                  <span className={styles.separator}>+</span>
                  <SourceBadge name="GitLab" colors={['red']} />
                </div>
              </td>

              <td>Критическая остановка</td>
            </tr>

            <tr>
              <th scope="row">
                <span className={styles.status}>
                  <Dot color="gray" />
                  Технический статус
                </span>
              </th>

              <td>
                <div className={styles.sources}>
                  <span className={styles.sourceBadge}>Импорт</span>
                  <span className={styles.separator}>/</span>
                  <span className={styles.sourceBadge}>Нет связи</span>
                </div>
              </td>

              <td>Идёт / требуется синхронизация данных</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className={styles.footer}>
        Указаны пороги по умолчанию. Дни задаются отдельно для каждого
        проекта в его настройках.
      </p>
    </dialog>
  )
}