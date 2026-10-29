import { LoaderCircle } from 'lucide-react'

import styles from './ProjectLoadingCard.module.css'

interface ProjectLoadingCardProps {
  name: string
}

export function ProjectLoadingCard({
  name,
}: ProjectLoadingCardProps) {
  return (
    <article
      className={styles.card}
      aria-busy="true"
      aria-label={`Загрузка данных проекта «${name}»`}
    >
      <h2 className={styles.title}>{name}</h2>

      <div className={styles.badge}>
        <span className={styles.dot} aria-hidden="true" />
        Загрузка данных
      </div>

      <div
        className={`${styles.skeleton} ${styles.short}`}
        aria-hidden="true"
      />

      <p className={styles.message} role="status">
        <LoaderCircle
          className={styles.spinner}
          size={18}
          aria-hidden="true"
        />
        Данные проекта загружаются…
      </p>

      <div className={styles.lines} aria-hidden="true">
        <div className={styles.skeleton} />
        <div className={`${styles.skeleton} ${styles.medium}`} />
      </div>

      <p className={styles.hint}>
        Это может занять некоторое время
      </p>
    </article>
  )
}