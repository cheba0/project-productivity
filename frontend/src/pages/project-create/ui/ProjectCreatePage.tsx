import { useState } from 'react'
import { Link } from 'react-router'

import styles from './ProjectCreatePage.module.css'

export function ProjectCreatePage() {
  const [warningDays, setWarningDays] = useState('7')

  return (
    <section className={styles.page} aria-labelledby="project-create-title">
      <header className={styles.heading}>

        <h1 id="project-create-title">Новый проект</h1>
        <p>Данные загрузятся через некоторое время после создания</p>
      </header>

      <form
        className={styles.form}
        onSubmit={(event) => event.preventDefault()}
      >
        <section className={styles.panel} aria-labelledby="basic-title">
          <h2 id="basic-title">Основное</h2>

          <label className={styles.field}>
            <span>Название проекта</span>
            <input
              name="name"
              type="text"
              placeholder="Например, TPU.Metrics"
            />
          </label>

          <label className={styles.field}>
            <span>Ссылка на витрину проектов</span>
            <input
              name="showcaseUrl"
              type="url"
              placeholder="https://..."
            />
          </label>
        </section>

        <section className={styles.panel} aria-labelledby="integrations-title">
          <h2 id="integrations-title">Интеграции</h2>

          <div className={styles.integrations}>
            <fieldset className={styles.integration}>
              <legend>GitLab</legend>

              <label className={styles.field}>
                <span>Ссылка</span>
                <input
                  name="gitlabUrl"
                  type="url"
                  placeholder="https://gitlab..."
                />
              </label>

              <label className={styles.field}>
                <span>Токен</span>
                <input
                  name="gitlabToken"
                  type="text"
                  placeholder="Введите токен"
                  autoComplete="off"
                />
              </label>
            </fieldset>

            <fieldset className={styles.integration}>
              <legend>Redmine</legend>

              <label className={styles.field}>
                <span>Ссылка</span>
                <input
                  name="redmineUrl"
                  type="url"
                  placeholder="https://redmine..."
                />
              </label>

              <label className={styles.field}>
                <span>Токен</span>
                <input
                  name="redmineToken"
                  type="text"
                  placeholder="Введите токен"
                  autoComplete="off"
                />
              </label>
            </fieldset>
          </div>
        </section>

        <section className={styles.panel} aria-labelledby="thresholds-title">
          <h2 id="thresholds-title">Дни для статусов</h2>

          <p className={styles.hint}>
            Дни без активности в GitLab и Redmine. Свои значения для каждого
            проекта.
          </p>

          <div className={styles.statusRow}>
            <label className={styles.statusLabel} htmlFor="active-days">
              <span
                className={`${styles.dot} ${styles.green}`}
                aria-hidden="true"
              />
              Идёт работа / Активен
            </label>

            <div className={styles.threshold}>
              <span>до</span>
              <input
                id="active-days"
                name="activeDays"
                type="number"
                min="1"
                step="1"
                defaultValue="3"
              />
              <span>дн.</span>
            </div>
          </div>

          <div className={styles.statusRow}>
            <label className={styles.statusLabel} htmlFor="warning-days">
              <span
                className={`${styles.dot} ${styles.yellow}`}
                aria-hidden="true"
              />
              Замедление
            </label>

            <div className={styles.threshold}>
              <span>до</span>
              <input
                id="warning-days"
                name="warningDays"
                type="number"
                min="1"
                step="1"
                value={warningDays}
                onChange={(event) => setWarningDays(event.target.value)}
              />
              <span>дн.</span>
            </div>
          </div>

          <div className={styles.statusRow}>
            <span className={styles.statusLabel}>
              <span
                className={`${styles.dot} ${styles.red}`}
                aria-hidden="true"
              />
              Простой
            </span>

            <span className={styles.hint}>
              более {warningDays || '—'} дн.
            </span>
          </div>
        </section>

        <footer className={styles.actions}>
          <button className={styles.createButton} type="button">
            Создать проект
          </button>

          <Link className={styles.cancelButton} to="/">
            Отмена
          </Link>
        </footer>
      </form>
    </section>
  )
}