import {useRef, useState} from 'react'

import {Button} from '@/shared/ui/button'
import {Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle} from '@/shared/ui/dialog'

import type {ProjectDto} from '../../../entities/project/api/getProjects'
import {setProjectArchived} from '../../../entities/project/api/setProjectArchived'

interface ProjectArchiveControlProps {
  project: ProjectDto
  canManage: boolean
  disabled: boolean
  onBusyChange: (busy: boolean) => void
  onChanged: (project: ProjectDto) => void
}

export function ProjectArchiveControl({
  project, canManage, disabled, onBusyChange, onChanged,
}: ProjectArchiveControlProps) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const submitting = useRef(false)

  const archived = project.archived_at !== null

  function close() {
    if (submitting.current) return
    setOpen(false)
    setError(null)
  }

  async function confirm() {
    if (!canManage || submitting.current || disabled) return

    submitting.current = true
    setBusy(true)
    onBusyChange(true)
    setError(null)

    try {
      const updated = await setProjectArchived(project.id, !archived)
      onChanged(updated)
      setOpen(false)
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Не удалось изменить состояние проекта.')
    } finally {
      submitting.current = false
      setBusy(false)
      onBusyChange(false)
    }
  }

  if (!canManage) return null

  return (
    <>
      <button
        type="button" disabled={disabled || busy}
        className="border-0 bg-transparent px-0 py-2 text-xs font-semibold text-[#65736a] hover:text-[#18201c] hover:underline disabled:cursor-not-allowed disabled:opacity-50"
        onClick={() => {
            setError(null)
            setOpen(true)
        }}
      >
        {archived ? 'Восстановить' : 'В архив'}
      </button>

      <Dialog open={open} onOpenChange={(nextOpen) => {
        if (!nextOpen) close()
      }}>
        <DialogContent className="rounded-2xl bg-white p-5 text-[#18201c] sm:max-w-[440px]">
          <DialogHeader className="text-left">
            <DialogTitle className="text-base">
              {archived ? 'Восстановить проект?' : 'Перенести проект в архив?'}
            </DialogTitle>

            <DialogDescription className="text-xs leading-relaxed text-[#748079]">
              {archived
                ? `Проект «${project.name}» вернётся в обычный список проектов.`
                : `Проект «${project.name}» будет перенесён в архив. Его можно восстановить позже.`}
            </DialogDescription>
          </DialogHeader>

          <p className="text-xs text-[#748079]">
            Изменения в полях настроек этим действием не сохраняются.
          </p>

          {error && <p role="alert" className="text-xs text-[#b42318]">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button
              type="button" variant="outline" disabled={busy || disabled}
              className="border-[#22bf45] bg-[#e6f7eb] text-[#18201c] hover:bg-[#d8f2df]"
              onClick={() => void confirm()}
            >
              {busy ? 'Выполняем…' : archived ? 'Восстановить' : 'В архив'}
            </Button>

            <Button type="button" variant="outline" disabled={busy} onClick={close}>
              Отмена
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}