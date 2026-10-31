"""API for project/student dashboards, computed from a PostgreSQL snapshot.

FRONTEND: send credentials: 'include' for TPU session cookies.
GET endpoints do not contact GitLab/Redmine and do not invent missing metrics.
"""
from collections import Counter
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.app.database import get_db
from auth_service.app.models import User
from auth_service.app.project_models import ProjectMember, ProjectMetricSnapshot
from auth_service.app.services.dashboard_extras import sprint_hours, upcoming_deadlines
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


def _profiles(db, members):
    ids = [member.id for member in members]
    if not ids:
        return {}
    return {
        profile.member_id: profile
        for profile in db.scalars(
            select(MemberProfile).where(MemberProfile.member_id.in_(ids))
        ).all()
    }


def _dashboard(project, db, sprint, start, end):
    first, last = _period(project, sprint, start, end)
    members, users = _members(db, project)
    data = get_cached_data(db, project, first, last)
    result = compute(
        data, members, users, first, last,
        profiles=_profiles(db, members),
        active_after_days=project.active_after_days,
        delayed_after_days=project.delayed_after_days,
    )
    result['sprint_hours'] = sprint_hours(data, project, first, last)
    result['upcoming_deadlines'] = upcoming_deadlines(data)
    return result


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


def _snapshot_window(db, project, start, end):
    if bool(start) != bool(end):
        raise HTTPException(422, 'Both start and end required')
    snapshot = db.get(ProjectMetricSnapshot, project.id)
    if not snapshot or not snapshot.period_start or not snapshot.period_end:
        raise HTTPException(409, 'No metrics snapshot; sync this project first')
    first = start or snapshot.period_start
    last = end or snapshot.period_end
    return get_cached_data(db, project, first, last), first, last


@router.get('/{project_id}/sprint-hours')
def get_sprint_hours(project_id: UUID, start: date | None = None,
                     end: date | None = None,
                     db: Session = Depends(get_db),
                     user: User = Depends(require_user)):
    """Full cached window by default, rather than only the current sprint."""
    project = load_project(db, project_id, user)
    data, first, last = _snapshot_window(db, project, start, end)
    return {
        'period': {'start': first.isoformat(), 'end': last.isoformat()},
        'sources': data['sources'],
        **sprint_hours(data, project, first, last),
    }


@router.get('/{project_id}/deadlines')
def get_deadlines(project_id: UUID, days: int = Query(14, ge=1, le=365),
                  limit: int = Query(25, ge=1, le=100),
                  db: Session = Depends(get_db),
                  user: User = Depends(require_user)):
    """Current deadlines from the last successful PostgreSQL snapshot."""
    project = load_project(db, project_id, user)
    data, _, _ = _snapshot_window(db, project, None, None)
    return {'sources': data['sources'],
            **upcoming_deadlines(data, days=days, limit=limit)}


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
    members, users = _members(db, project)
    result = compute(
        data, members, users, first, last,
        profiles=_profiles(db, members),
        active_after_days=project.active_after_days,
        delayed_after_days=project.delayed_after_days,
    )
    student = next(s for s in result['students'] if s['member_id'] == str(member.id))
    git_email = (profile.gitlab_email if profile and profile.gitlab_email else member.email).lower()
    commits = [c for c in data['commits'] if (c.get('author_email') or '').lower() == git_email]
    red_id = profile.redmine_user_id if profile else None
    red_entries = [e for e in data['entries'] if str((e.get('user') or {}).get('id')) == str(red_id)] if red_id else []
    assigned = [t for t in result['tasks'] if red_id and str(t['assigned_to']) == str(red_id)]
    commits_per_day = Counter(
        (c.get('committed_date') or c.get('created_at') or '')[:10]
        for c in commits
    )
    entries_per_day = Counter(e.get('spent_on') for e in red_entries)
    hours_per_day = {}
    for entry in red_entries:
        day = entry.get('spent_on')
        if day:
            hours_per_day[day] = hours_per_day.get(day, 0) + float(entry.get('hours') or 0)
    activity = []
    active_weeks = set()
    for row in result['daily_activity']:
        day = row['date']
        git_count = commits_per_day[day]
        red_count = entries_per_day[day] if red_id is not None else None
        kind = ('both' if git_count and red_count else
                'gitlab' if git_count else
                'redmine' if red_count else 'none')
        parsed_day = date.fromisoformat(day)
        if kind != 'none':
            active_weeks.add(parsed_day.isocalendar()[:2])
        activity.append({
            'date': day,
            'gitlab_commits': git_count,
            # This is the number of logged time entries, not a count of issue
            # history changes (which the legacy analytics schema lacks).
            'redmine_updates': red_count,
            'redmine_hours': round(hours_per_day.get(day, 0), 2)
                if red_id is not None else None,
            'activity_kind': kind,
            'is_weekend': parsed_day.weekday() >= 5,
        })

    return {
        'profile': _profile(db, member),
        'period': result['period'], 'sources': result['sources'],
        'summary': {
            'commits': student['gitlab_commits'],
            'redmine_entries': student['redmine_entries'],
            'actual_hours': student['actual_hours'],
            'planned_hours': student['planned_hours'],
            'hours_deviation': student['hours_deviation'],
            'hours_deviation_percent': student['hours_deviation_percent'],
            'tasks_total': student['tasks_total'],
            'tasks_done': student['tasks_done'],
            'tasks_in_progress': student['tasks_in_progress'],
            'last_gitlab_activity': student['last_gitlab_activity'],
            'last_redmine_activity': student['last_redmine_activity'],
            'gitlab_inactive_days': student['gitlab_inactive_days'],
            'redmine_inactive_days': student['redmine_inactive_days'],
            'activity_status': student['activity_status'],
            'active_weeks': len(active_weeks),
        },
        'daily_activity': activity,
    }


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
