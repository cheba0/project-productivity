import { useId, useRef, useState, type FormEvent } from 'react'

import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'

import { addProjectMember } from '../../../entities/project/api/addProjectMember'
import type { ProjectDto } from '../../../entities/project/api/getProjects'

interface AddMemberDialogProps {
  projectId: string
  open: boolean
  onClose: () => void
  onAdded: (member: ProjectDto['members'][number]) => void
}

export function AddMemberDialog({
  projectId,
  open,
  onClose,
  onAdded,
}: AddMemberDialogProps) {
  const emailId = useId()
  const roleId = useId()

  const submitting = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (submitting.current) return

    const form = event.currentTarget
    const data = new FormData(form)

    const email = String(data.get('email') ?? '').trim()
    const role = String(data.get('role') ?? '').trim()

    if (!email || !role) {
      setError('Укажите почту и роль участника.')
      return
    }

    submitting.current = true
    setSaving(true)
    setError(null)

    try {
      const member = await addProjectMember(projectId, {
        email,
        role,
      })

      onAdded(member)
      form.reset()
      onClose()
    } catch (reason: unknown) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'Не удалось добавить участника.',
      )
    } finally {
      submitting.current = false
      setSaving(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen && !submitting.current) {
          setError(null)
          onClose()
        }
      }}
    >
      <DialogContent className="gap-0 rounded-2xl bg-white p-5 text-[#18201c] sm:max-w-[360px]">
        <DialogHeader className="text-left">
          <DialogTitle className="text-base font-bold">
            Добавить участника
          </DialogTitle>

          <DialogDescription className="sr-only">
            Укажите почту и роль нового участника проекта.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-5 grid gap-4">
          <div className="grid gap-2">
            <Label
              htmlFor={emailId}
              className="text-xs font-normal text-[#748079]"
            >
              Почта студента
            </Label>

            <Input
              id={emailId}
              name="email"
              type="email"
              placeholder="student@tpu.ru"
              maxLength={255}
              required
              disabled={saving}
              className="h-9 rounded-md bg-white text-sm"
            />
          </div>

          <div className="grid gap-2">
            <Label
              htmlFor={roleId}
              className="text-xs font-normal text-[#748079]"
            >
              Роль
            </Label>

            <Input
              id={roleId}
              name="role"
              type="text"
              placeholder="Например, Frontend-разработчик"
              maxLength={100}
              required
              disabled={saving}
              className="h-9 rounded-md bg-white text-sm"
            />
          </div>

          <p className="text-xs leading-relaxed text-[#748079]">
            Ссылки и токены на GitLab и Redmine студент добавит сам в своём профиле
          </p>

          {error && (
            <p role="alert" className="text-sm text-[#b42318]">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="submit"
              disabled={saving}
              variant="outline"
              className="h-9 border-[#22bf45] bg-[#e6f7eb] text-[#18201c] hover:bg-[#d8f2df]"
            >
              {saving ? 'Добавляем…' : 'Добавить'}
            </Button>

            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={() => {
                setError(null)
                onClose()
              }}
              className="h-9 bg-white"
            >
              Отмена
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}