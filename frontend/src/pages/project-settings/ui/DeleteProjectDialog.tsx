import {useId, useRef, useState, type FormEvent} from 'react'
import {useNavigate} from 'react-router'

import {Button} from '@/shared/ui/button'
import {Input} from '@/shared/ui/input'
import {Label} from '@/shared/ui/label'
import {Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle} from '@/shared/ui/dialog'

import {deleteProject} from '../../../entities/project/api/deleteProject'
import {useProjectSyncStore} from '../../../store/projectSyncStore'
interface DeleteProjectDialogProps {
  projectId: string
  projectName: string
  open: boolean
  onClose: () => void
}

export function DeleteProjectDialog({projectId, projectName, open, onClose}: DeleteProjectDialogProps) {
  const navigate = useNavigate()
  const inputId = useId()
  const submitting = useRef(false)

  const [confirmation, setConfirmation] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const confirmed = projectName.length > 0 && confirmation === projectName

  function close() {
    if (submitting.current) return

    setConfirmation('')
    setError(null)
    onClose()
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!confirmed || submitting.current) return

    submitting.current = true
    setDeleting(true)
    setError(null)

    try {
      await deleteProject(projectId, confirmation)

      setConfirmation('')
      onClose()
      navigate('/', {replace: true})
      useProjectSyncStore.getState().invalidateProjects()
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Не удалось удалить проект.')
    } finally {
      submitting.current = false
      setDeleting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => {
      if (!nextOpen) close()
    }}>
      <DialogContent className="rounded-2xl bg-white p-5 text-[#18201c] sm:max-w-[440px]">
        <DialogHeader className="text-left">
          <DialogTitle className="text-base font-bold">Удалить проект?</DialogTitle>

          <DialogDescription className="text-xs leading-relaxed text-[#748079]">
            Проект «{projectName}» и все его данные будут удалены без возможности восстановления.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="grid gap-4" aria-busy={deleting}>
          <div className="grid gap-2">
            <Label htmlFor={inputId} className="text-xs font-normal text-[#58655e]">
              Для подтверждения введите точное название проекта
            </Label>

            <Input
              id={inputId} name="projectNameConfirmation"
              value={confirmation} onChange={(event) => {
                setConfirmation(event.target.value)
                setError(null)
              }}
              placeholder="Название проекта" autoComplete="off" spellCheck={false}
              disabled={deleting} required className="h-9 bg-white"
            />
          </div>

          {error && <p role="alert" className="text-xs text-[#b42318]">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button
              type="submit" variant="outline" disabled={!confirmed || deleting}
              className="border-[#22bf45] bg-[#e6f7eb] text-[#18201c] hover:bg-[#d8f2df]"
            >
              {deleting ? 'Удаляем…' : 'Удалить проект'}
            </Button>

            <Button type="button" variant="outline" disabled={deleting} onClick={close}>
              Отмена
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}