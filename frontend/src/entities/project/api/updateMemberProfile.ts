export interface MemberProfile {
  member_id: string
  name: string | null
  email: string
  role: string
  phone: string | null
  telegram: string | null
  gitlab_profile_url: string | null
  redmine_profile_url: string | null
  gitlab_email: string | null
  redmine_user_id: number | null
}

export interface MemberProfileUpdate {
  gitlab_email?: string | null
  redmine_user_id?: number | null
}

export async function updateMemberProfile(
  projectId: string,
  memberId: string,
  payload: MemberProfileUpdate,
): Promise<MemberProfile> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectId)}` +
      `/members/${encodeURIComponent(memberId)}/profile`,
    {
      method: 'PATCH',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    },
  )

  const body = await response.json().catch(() => null)

  if (!response.ok) {
    const fallback =
      response.status === 403
        ? 'Изменять профиль может сам участник или владелец проекта.'
        : response.status === 401
          ? 'Сессия истекла. Войдите снова.'
          : `Не удалось сохранить профиль: HTTP ${response.status}`

    throw new Error(
      typeof body?.detail === 'string'
        ? body.detail
        : typeof body?.detail?.message === 'string'
          ? body.detail.message
          : fallback,
    )
  }

  return body
}