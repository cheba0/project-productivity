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

import {
  updateMemberProfile,
  type MemberProfile,
} from '../../../entities/project/api/updateMemberProfile'

interface EditMemberDialogProps {
  projectId: string
  profile: MemberProfile
  onClose: () => void
  onSaved: (profile: MemberProfile) => void
}

function optionalText(data: FormData, key: string): string | null {
  const value = String(data.get(key) ?? '').trim()
  return value || null
}

function profileUrl(data: FormData, key: string): string | null {
  const value = optionalText(data, key)

  if (!value) return null

  const url = new URL(value)

  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error('Ссылки должны начинаться с http:// или https://.')
  }

  return url.href
}

export function EditMemberDialog({
  projectId,
  profile,
  onClose,
  onSaved,
}: EditMemberDialogProps) {
  const prefix = useId()
  const submitting = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (submitting.current) return

    const data = new FormData(event.currentTarget)

    try {
      const redmineValue = optionalText(data, 'redmine_user_id')
      const redmineId =
        redmineValue === null ? null : Number(redmineValue)

      if (
        redmineId !== null &&
        (!Number.isSafeInteger(redmineId) || redmineId < 1)
      ) {
        throw new Error('Redmine ID должен быть целым числом больше нуля.')
      }

      const payload = {
        phone: optionalText(data, 'phone'),
        telegram: optionalText(data, 'telegram'),
        gitlab_profile_url: profileUrl(data, 'gitlab_profile_url'),
        redmine_profile_url: profileUrl(data, 'redmine_profile_url'),
        gitlab_email: optionalText(data, 'gitlab_email'),
        redmine_user_id: redmineId,
      }

      submitting.current = true
      setSaving(true)
      setError(null)

      const updated = await updateMemberProfile(
        projectId,
        profile.member_id,
        payload,
      )

      onSaved(updated)
      onClose()
    } catch (reason: unknown) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'Не удалось сохранить профиль.',
      )
    } finally {
      submitting.current = false
      setSaving(false)
    }
  }

  const fieldClass = 'grid gap-2'
  const labelClass = 'text-xs font-normal text-[#748079]'
  const inputClass = 'h-9 rounded-md bg-white'

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !submitting.current) onClose()
      }}
    >
      <DialogContent className="max-h-[90dvh] overflow-y-auto rounded-2xl bg-white p-5 text-[#18201c] sm:max-w-[520px]">
        <DialogHeader className="text-left">
          <DialogTitle>Личные данные</DialogTitle>
          <DialogDescription className="sr-only">
            Контактные данные и привязки аккаунтов участника.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className={fieldClass}>
            <Label htmlFor={`${prefix}-name`} className={labelClass}>
              Фамилия Имя Отчество
            </Label>
            <Input
              id={`${prefix}-name`}
              value={profile.name || 'Имя ещё не получено'}
              disabled
              className="h-9 bg-[#eef2ef]"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className={fieldClass}>
              <Label htmlFor={`${prefix}-email`} className={labelClass}>
                Email
              </Label>
              <Input
                id={`${prefix}-email`}
                value={profile.email}
                disabled
                className="h-9 bg-[#eef2ef]"
              />
            </div>

            <div className={fieldClass}>
              <Label htmlFor={`${prefix}-phone`} className={labelClass}>
                Телефон
              </Label>
              <Input
                id={`${prefix}-phone`}
                name="phone"
                type="tel"
                defaultValue={profile.phone ?? ''}
                placeholder="+7 000 000-00-00"
                maxLength={50}
                disabled={saving}
                className={inputClass}
              />
            </div>
          </div>

          <div className={fieldClass}>
            <Label htmlFor={`${prefix}-telegram`} className={labelClass}>
              Telegram
            </Label>
            <Input
              id={`${prefix}-telegram`}
              name="telegram"
              defaultValue={profile.telegram ?? ''}
              placeholder="@username"
              maxLength={100}
              disabled={saving}
              className={inputClass}
            />
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <fieldset className="m-0 grid min-w-0 gap-3 border-0 p-0">
              <legend className="mb-3 text-sm font-bold">GitLab</legend>

              <div className={fieldClass}>
                <Label htmlFor={`${prefix}-gitlab-url`} className={labelClass}>
                  Ссылка на профиль
                </Label>
                <Input
                  id={`${prefix}-gitlab-url`}
                  name="gitlab_profile_url"
                  type="url"
                  defaultValue={profile.gitlab_profile_url ?? ''}
                  placeholder="https://gitlab.com/username"
                  disabled={saving}
                  className={inputClass}
                />
              </div>

              <div className={fieldClass}>
                <Label htmlFor={`${prefix}-gitlab-email`} className={labelClass}>
                  Email автора коммитов
                </Label>
                <Input
                  id={`${prefix}-gitlab-email`}
                  name="gitlab_email"
                  type="email"
                  defaultValue={profile.gitlab_email ?? ''}
                  placeholder="developer@example.org"
                  maxLength={255}
                  disabled={saving}
                  className={inputClass}
                />
              </div>
            </fieldset>

            <fieldset className="m-0 grid min-w-0 gap-3 border-0 p-0">
              <legend className="mb-3 text-sm font-bold">Redmine</legend>

              <div className={fieldClass}>
                <Label htmlFor={`${prefix}-redmine-url`} className={labelClass}>
                  Ссылка на профиль
                </Label>
                <Input
                  id={`${prefix}-redmine-url`}
                  name="redmine_profile_url"
                  type="url"
                  defaultValue={profile.redmine_profile_url ?? ''}
                  placeholder="https://redmine.example.org/users/12"
                  disabled={saving}
                  className={inputClass}
                />
              </div>

              <div className={fieldClass}>
                <Label htmlFor={`${prefix}-redmine-id`} className={labelClass}>
                  ID пользователя
                </Label>
                <Input
                  id={`${prefix}-redmine-id`}
                  name="redmine_user_id"
                  type="number"
                  min={1}
                  step={1}
                  defaultValue={profile.redmine_user_id ?? ''}
                  placeholder="12"
                  disabled={saving}
                  className={inputClass}
                />
              </div>
            </fieldset>
          </div>

          <p className="text-xs leading-relaxed text-[#748079]">
            GitLab-email используется для поиска коммитов.
            Redmine ID — для задач и трудозатрат.
            Пустой Redmine ID удалит привязку; пустой GitLab-email
            вернёт поиск по email участника.
          </p>

          {error && (
            <p role="alert" className="text-sm text-[#b42318]">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <Button
              type="submit"
              variant="outline"
              disabled={saving}
              className="border-[#22bf45] bg-[#e6f7eb] text-[#18201c] hover:bg-[#d8f2df]"
            >
              {saving ? 'Сохраняем…' : 'Сохранить'}
            </Button>

            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={onClose}
            >
              Отмена
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}