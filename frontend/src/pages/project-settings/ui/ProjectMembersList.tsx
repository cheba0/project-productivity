import {useRef, useState, type FormEvent} from 'react'
import {Link} from 'react-router'
import {X} from 'lucide-react'

import {Button} from '@/shared/ui/button'
import {Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle} from '@/shared/ui/dialog'

import type {ProjectDto} from '../../../entities/project/api/getProjects'
import {removeProjectMember} from '../../../entities/project/api/removeProjectMember'

type Member = ProjectDto['members'][number]

interface ProjectMembersListProps {
  projectId: string
  members: Member[]
  canManage: boolean
  disabled?: boolean
  onRemoved: (memberId: string) => void
}

function initials(value: string): string {
  return value.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

function roleLabel(value: string): string {
  if (value === 'owner') return 'Владелец проекта'
  if (value === 'member') return 'Участник'
  return value
}

const avatarColors = ['#c4efd0', '#d8d9ff', '#ffe0e7', '#fff0cb', '#dcf0fa']

export function ProjectMembersList({
  projectId, members, canManage, disabled = false, onRemoved,
}: ProjectMembersListProps) {
  const [selected, setSelected] = useState<Member | null>(null)

  return (
    <>
      <ul className="m-0 list-none p-0">
        {members.map((member, index) => (
          <li
            key={member.id}
            className="flex items-center gap-2 border-0 border-b border-solid border-[#edf0ee] last:border-b-0"
          >
            <Link
              to={`/projects/${projectId}/members/${member.id}`}
              className="flex min-w-0 flex-1 items-center gap-3 rounded-lg py-3 text-inherit no-underline hover:bg-[#f5f7f6]"
            >
              <span
                className="flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                style={{backgroundColor: avatarColors[index % avatarColors.length]}}
                aria-hidden="true"
              >
                {initials(member.name || member.email)}
              </span>

              <span className="grid min-w-0 gap-1">
                <strong className="break-words text-xs">{member.name || member.email}</strong>
                <span className="text-[11px] leading-relaxed text-[#748079]">
                  {roleLabel(member.role)}{member.is_pending ? ' · Ещё не вошёл в приложение' : ''}
                </span>
              </span>
            </Link>

            {canManage && !member.is_owner && (
              <Button
                type="button" variant="ghost" size="icon"
                disabled={disabled} onClick={() => setSelected(member)}
                className="size-8 shrink-0 !bg-transparent !shadow-none text-[#85918a] hover:text-[#c62844]"
                aria-label={`Удалить участника ${member.name || member.email}`}
                title="Удалить из проекта"
              >
                <X size={17} aria-hidden="true" />
              </Button>
            )}
          </li>
        ))}
      </ul>

      {members.length === 0 && (
        <p className="text-sm text-[#748079]">Участников пока нет.</p>
      )}

      {selected && (
        <RemoveMemberDialog
          key={selected.id} projectId={projectId} member={selected}
          onClose={() => setSelected(null)} onRemoved={onRemoved}
        />
      )}
    </>
  )
}

interface RemoveMemberDialogProps {
  projectId: string
  member: Member
  onClose: () => void
  onRemoved: (memberId: string) => void
}

function RemoveMemberDialog({projectId, member, onClose, onRemoved}: RemoveMemberDialogProps) {
  const submitting = useRef(false)
  const [removing, setRemoving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function close() {
    if (!submitting.current) onClose()
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    event.stopPropagation()

    if (submitting.current) return

    submitting.current = true
    setRemoving(true)
    setError(null)

    try {
      await removeProjectMember(projectId, member.id)
      onRemoved(member.id)
      onClose()
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Не удалось удалить участника.')
    } finally {
      submitting.current = false
      setRemoving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(open) => {
      if (!open) close()
    }}>
      <DialogContent className="rounded-2xl bg-white p-5 text-[#18201c] sm:max-w-[420px]">
        <DialogHeader className="text-left">
          <DialogTitle className="text-base">Удалить участника?</DialogTitle>
          <DialogDescription className="text-xs leading-relaxed text-[#748079]">
            Участник «{member.name || member.email}» будет исключён из этого проекта.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="grid gap-4" aria-busy={removing}>
          {error && <p role="alert" className="text-xs text-[#b42318]">{error}</p>}

          <div className="flex justify-end gap-2">
            <Button
              type="submit" variant="outline" disabled={removing}
              className="border-[#c62844] bg-[#fff0f3] text-[#c62844] hover:bg-[#ffe1e8]"
            >
              {removing ? 'Удаляем…' : 'Удалить'}
            </Button>

            <Button type="button" variant="outline" disabled={removing} onClick={close}>
              Отмена
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}