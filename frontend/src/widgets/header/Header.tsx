import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { Link, useMatch } from 'react-router'

import {
  getProject,
  type ProjectDto,
} from '../../entities/project'

import { useProjectHeaderStore } from '../../store/projectHeaderStore'

const linkClass =
  'text-[#859088] no-underline hover:text-[#169a37] ' +
  'focus-visible:rounded-sm focus-visible:outline-2 ' +
  'focus-visible:outline-offset-2 focus-visible:outline-[#22bf45]'

export function Header() {
  const createMatch = useMatch('/projects/new')
  const settingsMatch = useMatch('/projects/:projectId/settings')
  const projectMatch = useMatch('/projects/:projectId')
  const memberMatch = useMatch(
    '/projects/:projectId/members/:memberId',
  )

  const isCreatePage = Boolean(createMatch)
  const isSettingsPage = Boolean(settingsMatch)
  const isMemberPage = Boolean(memberMatch)

  const showSprintControls =
    !isCreatePage &&
    (Boolean(projectMatch) || isMemberPage)

  const projectId = isCreatePage
    ? undefined
    : settingsMatch?.params.projectId ??
      memberMatch?.params.projectId ??
      projectMatch?.params.projectId

  const memberId = memberMatch?.params.memberId

  const setControlsElement = useProjectHeaderStore(
    (state) => state.setControlsElement,
  )

  const [loadedProject, setLoadedProject] =
    useState<ProjectDto | null>(null)

  useEffect(() => {
    if (!projectId) return

    const controller = new AbortController()

    getProject(projectId, controller.signal)
      .then((project) => {
        if (controller.signal.aborted) return

        setLoadedProject(project)
      })
      .catch(() => {
        if (controller.signal.aborted) return

        // Основную ошибку загрузки показывает страница.
        setLoadedProject(null)
      })

    return () => controller.abort()
  }, [projectId, memberId])

  // Не показываем название предыдущего проекта
  // во время перехода на другой маршрут.
  const currentProject =
    loadedProject !== null && loadedProject.id === projectId
      ? loadedProject
      : null

  const projectName = currentProject?.name || 'Проект'

  const member = currentProject?.members.find(
    (item) => item.id === memberId,
  )

  const memberName =
    member?.name?.trim() || member?.email || 'Участник'

  return (
    <header className="flex min-h-[64px] flex-wrap items-center justify-between gap-x-5 gap-y-3 border-0 border-b border-solid border-[#e5eae7] bg-white px-4 py-3 sm:px-6">
      <div className="min-w-0">
        {isCreatePage || projectId ? (
          <nav
            className="flex min-w-0 flex-wrap items-center gap-2 text-[13px]"
            aria-label="Навигационная цепочка"
          >
            <Link className={linkClass} to="/">
              Проекты
            </Link>

            <span className="text-[#9aa49e]" aria-hidden="true">
              ›
            </span>

            {isCreatePage ? (
              <span
                className="font-bold text-[#18201c]"
                aria-current="page"
              >
                Новый проект
              </span>
            ) : isMemberPage ? (
              <>
                <Link
                  className={`${linkClass} break-words`}
                  to={`/projects/${projectId}`}
                >
                  {projectName}
                </Link>

                <span
                  className="text-[#9aa49e]"
                  aria-hidden="true"
                >
                  ›
                </span>

                <span
                  className="break-words font-bold text-[#18201c]"
                  aria-current="page"
                >
                  {memberName}
                </span>
              </>
            ) : isSettingsPage ? (
              <>
                <Link
                  className={`${linkClass} break-words`}
                  to={`/projects/${projectId}`}
                >
                  {projectName}
                </Link>

                <span
                  className="text-[#9aa49e]"
                  aria-hidden="true"
                >
                  ›
                </span>

                <span
                  className="font-bold text-[#18201c]"
                  aria-current="page"
                >
                  Настройки
                </span>
              </>
            ) : (
              <span
                className="break-words font-bold text-[#18201c]"
                aria-current="page"
              >
                {projectName}
              </span>
            )}
          </nav>
        ) : (
          <span className="text-[15px] font-bold text-[#18201c]">
            Проекты
          </span>
        )}
      </div>

      <div className="ml-auto flex min-w-0 items-center">
        {showSprintControls ? (
          <div
            ref={setControlsElement}
            className="flex min-w-0 items-center"
          />
        ) : (
          <label className="hidden min-h-10 w-[220px] items-center gap-2.5 rounded-[10px] border border-solid border-[#e1e7e3] bg-[#f5f7f6] px-3 text-[#8c9790] md:flex xl:w-[280px]">
            <Search
              size={17}
              className="shrink-0"
              aria-hidden="true"
            />

            <input
              type="search"
              placeholder="Поиск по проектам и студентам…"
              aria-label="Поиск по проектам и студентам"
              disabled
              title="Поиск пока не подключён"
              className="min-w-0 w-full border-0 bg-transparent p-0 font-[inherit] text-xs text-[#8c9790] placeholder:text-[#8c9790]"
            />
          </label>
        )}
      </div>
    </header>
  )
}