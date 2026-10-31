"""API для страниц проекта и студента. FRONTEND: credentials: 'include'.

Все числовые показатели получаются при запросе из API GitLab/Redmine.
При недоступности интеграции возвращаем ошибку, не подменяем метрики нулями.
"""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.app.database import get_db
from auth_service.app.models import User
from auth_service.app.project_models import ProjectMember
from auth_service.app.projects_router import require_user, load_project
from auth_service.app.live_metrics import compute, sprint_dates, sprint_list
from auth_service.app.services.project_snapshot import get_cached_data, sync_project, sync_status
from auth_service.app.member_profile import MemberProfile
from auth_service.app.live_schemas import MemberProfileUpdate

router = APIRouter(prefix='/api/projects', tags=['Live dashboards'])


def _period(project, sprint, start, end):
    if sprint is not None:
        if start or end:
            raise HTTPException(422, 'Choose sprint OR start/end')
        return sprint_dates(project, sprint)
    if bool(start) != bool(end):
        raise HTTPException(422, 'Both start and end required')
    if start and end:
        return start, end
    # При отсутствии фильтра показываем текущий спринт, если известен старт.
    if project.start_date:
        elapsed = max(0, (date.today() - project.start_date).days)
        number = elapsed // (project.sprint_weeks * 7) + 1
        if project.deadline and date.today() > project.deadline:
            number = max(1, (project.deadline - project.start_date).days // (project.sprint_weeks * 7) + 1)
        return sprint_dates(project, number)
    raise HTTPException(409, 'Set project start_date or specify start/end')


def _members(db, project):
    members = db.scalars(select(ProjectMember).where(ProjectMember.project_id == project.id)).all()
    ids = [m.user_id for m in members if m.user_id]
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids))).all()} if ids else {}
    return members, users


def _dashboard(project, db, sprint, start, end):
    first, last = _period(project, sprint, start, end)
    members, users = _members(db, project)
    return compute(get_cached_data(db, project, first, last), members, users, first, last)


@router.get('/{project_id}/sprints')
def get_sprints(project_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user)
    return sprint_list(project)


@router.get('/{project_id}/dashboard')
def get_dashboard(project_id: UUID, sprint: int | None = Query(None, ge=1),
                  start: date | None = None, end: date | None = None,
                  db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user)
    return _dashboard(project, db, sprint, start, end)


@router.get('/{project_id}/workload')
def get_workload(project_id: UUID, sprint: int | None = Query(None, ge=1),
                 start: date | None = None, end: date | None = None,
                 db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user)
    result = _dashboard(project, db, sprint, start, end)
    return {'period': result['period'], 'tasks': result['tasks'], 'students': result['students'],
            'sources': result['sources']}


@router.get('/{project_id}/planning-quality')
def get_planning_quality(project_id: UUID, sprint: int | None = Query(None, ge=1),
                         start: date | None = None, end: date | None = None,
                         db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user)
    result = _dashboard(project, db, sprint, start, end)
    return {'period': result['period'], **result['planning_quality'], 'sources': result['sources']}


def _member(db, project, member_id):
    member = db.get(ProjectMember, member_id)
    if not member or member.project_id != project.id:
        raise HTTPException(404, 'Member not found')
    return member


def _profile(db, member):
    profile = db.get(MemberProfile, member.id)
    return {'member_id': str(member.id), 'name': member.user_id and (db.get(User, member.user_id).name if db.get(User, member.user_id) else None),
            'email': member.email, 'role': member.role,
            'phone': profile.phone if profile else None,
            'telegram': profile.telegram if profile else None,
            'gitlab_profile_url': profile.gitlab_profile_url if profile else None,
            'redmine_profile_url': profile.redmine_profile_url if profile else None,
            'redmine_user_id': profile.redmine_user_id if profile else None,
            'gitlab_email': profile.gitlab_email if profile else None}


@router.get('/{project_id}/members/{member_id}/dashboard')
def get_member_dashboard(project_id: UUID, member_id: UUID,
                         sprint: int | None = Query(None, ge=1),
                         start: date | None = None, end: date | None = None,
                         db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user)
    member = _member(db, project, member_id)
    profile = db.get(MemberProfile, member.id)
    first, last = _period(project, sprint, start, end)
    data = get_cached_data(db, project, first, last)
    result = compute(data, *_members(db, project), first, last)
    git_email = (profile.gitlab_email if profile and profile.gitlab_email else member.email).lower()
    commits = [c for c in data['commits'] if (c.get('author_email') or '').lower() == git_email]
    red_id = profile.redmine_user_id if profile else None
    red_entries = [e for e in data['entries'] if str((e.get('user') or {}).get('id')) == str(red_id)] if red_id else []
    assigned = [t for t in result['tasks'] if red_id and str(t['assigned_to']) == str(red_id)]
    return {'profile': _profile(db, member), 'period': result['period'],
            'sources': result['sources'],
            'summary': {'commits': len(commits), 'redmine_entries': len(red_entries) if red_id else None,
                        'actual_hours': round(sum(float(e.get('hours') or 0) for e in red_entries), 2) if red_id else None,
                        'tasks_total': len(assigned) if red_id else None,
                        'tasks_done': sum(t['done'] for t in assigned) if red_id else None,
                        'tasks_in_progress': sum(not t['done'] for t in assigned) if red_id else None},
            'daily_activity': [{'date': row['date'],
                                'gitlab_commits': sum((c.get('committed_date') or c.get('created_at') or '')[:10] == row['date'] for c in commits),
                                'redmine_updates': sum(e.get('spent_on') == row['date'] for e in red_entries) if red_id else None}
                               for row in result['daily_activity']]}


@router.get('/{project_id}/members/{member_id}/activity')
def get_member_activity(project_id: UUID, member_id: UUID, year: int | None = Query(None, ge=2000, le=2100),
                        month: int | None = Query(None, ge=1, le=12), period: str | None = None,
                        db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user)
    _member(db, project, member_id)
    if period == 'all':
        if not project.start_date:
            raise HTTPException(409, 'Project start_date required')
        # API ограничен годом на запрос; фронт может загружать годы отдельно.
        start = max(project.start_date, date.today() - timedelta(days=365))
        end = min(project.deadline or date.today(), date.today())
    elif year is not None and month is not None:
        start = date(year, month, 1)
        end = (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)) - timedelta(days=1)
    else:
        raise HTTPException(422, 'Specify year and month or period=all')
    result = get_member_dashboard(project_id, member_id, sprint=None, start=start, end=end, db=db, user=user)
    return {'profile': result['profile'], 'period': result['period'], 'sources': result['sources'],
            'daily_activity': result['daily_activity'], 'summary': result['summary']}


@router.patch('/{project_id}/members/{member_id}/profile')
def update_member_profile(project_id: UUID, member_id: UUID, payload: MemberProfileUpdate,
                          db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user)
    member = _member(db, project, member_id)
    if project.owner_id != user.id and member.user_id != user.id:
        raise HTTPException(403, 'Only owner or this member may edit profile')
    profile = db.get(MemberProfile, member.id)
    if profile is None:
        profile = MemberProfile(member_id=member.id)
        db.add(profile)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, str(value) if value is not None and key.endswith('_url') else value)
    db.commit()
    return _profile(db, member)

@router.get('/{project_id}/live-card')
def get_live_card(project_id: UUID, db: Session = Depends(get_db),
                  user: User = Depends(require_user)):
    """FRONTEND: карточка главной страницы, данные из API за последние 30 дней."""
    project = load_project(db, project_id, user)
    end = date.today()
    start = end - timedelta(days=29)
    result = _dashboard(project, db, None, start, end)
    return {'project_id': str(project.id), 'name': project.name,
            'is_paused': project.is_paused, 'archived_at': project.archived_at,
            'summary': result['summary'], 'daily_activity': result['daily_activity'],
            'sources': result['sources'], 'period': result['period']}

@router.get('/{project_id}/sync-status')
def get_sync_status(project_id: UUID, db: Session = Depends(get_db),
                    user: User = Depends(require_user)):
    return sync_status(db, load_project(db, project_id, user))


@router.post('/{project_id}/sync')
def refresh_metrics(project_id: UUID, db: Session = Depends(get_db),
                    user: User = Depends(require_user)):
    return sync_project(db, load_project(db, project_id, user, write=True))
