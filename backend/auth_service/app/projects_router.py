"""API списка проектов / настроек / участников по макетам.

FRONTEND: отправлять credentials: 'include' (авторизация через session_token).
Ни один ответ API не содержит секретные токены интеграций.
"""
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from auth_service.app.database import get_db
from auth_service.app.models import User, Workspace, WorkspaceMember
from auth_service.app.project_models import Project, ProjectActivity, ProjectMember
from auth_service.app.project_schemas import (
    ConfirmDelete, ProjectListFilter, ProjectListResponse, ProjectMemberCreate,
    ProjectMemberView, ProjectUpdate, ProjectView, ProjectWrite,
)
from auth_service.app.services.session_service import get_user_by_session

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Везде используем TPU-сессию, а не передаваемый с фронта user_id."""
    user = get_user_by_session(db, request.cookies.get("session_token"))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    # Приглашённый студент получает доступ после входа через ТПУ,
    # когда адрес email совпадает с адресом в приглашении.
    if user.email:
        email = user.email.strip().lower()
        invitations = db.scalars(select(ProjectMember).where(
            ProjectMember.user_id.is_(None), ProjectMember.email == email)).all()
        for invitation in invitations:
            invitation.user_id = user.id
            invitation.joined_at = datetime.now(timezone.utc)
            project = db.get(Project, invitation.project_id)
            if project and not db.scalar(select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == project.workspace_id,
                WorkspaceMember.user_id == user.id)):
                db.add(WorkspaceMember(workspace_id=project.workspace_id,
                                       user_id=user.id, role="viewer"))
        if invitations:
            db.commit()
    return user


def encrypt_token(value: str) -> bytes:
    # Без настроенного ключа запрещаем сохранять токены (никогда не пишем plaintext).
    from cryptography.fernet import Fernet
    key = os.getenv("PROJECT_TOKEN_ENCRYPTION_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="Project token encryption is not configured")
    try:
        return Fernet(key.encode()).encrypt(value.encode())
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Project token encryption key is invalid") from exc


def load_project(db: Session, project_id: UUID, user: User, *, write: bool = False) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        participant = db.scalar(select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        ))
        if participant is None:
            # Не раскрываем существование чужих проектов.
            raise HTTPException(status_code=404, detail="Project not found")
        if write:
            raise HTTPException(status_code=403, detail="Only project owner can change settings")
    return project


def member_view(member: ProjectMember, user_map: dict) -> ProjectMemberView:
    person = user_map.get(member.user_id)
    return ProjectMemberView(
        id=member.id, email=member.email, name=person.name if person else None,
        role=member.role, is_pending=member.user_id is None,
        is_owner=member.role == "owner",
    )


def activity_days(last_at: datetime | None) -> int | None:
    if last_at is None:
        return None
    return max(0, (datetime.now(timezone.utc) - last_at).days)


def project_view(db: Session, project: Project) -> ProjectView:
    participants = db.scalars(select(ProjectMember).where(ProjectMember.project_id == project.id)
                              .order_by(ProjectMember.created_at, ProjectMember.id)).all()
    user_ids = [member.user_id for member in participants if member.user_id]
    user_map = {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()} if user_ids else {}
    activity = db.get(ProjectActivity, project.id)
    gitlab_days = activity_days(activity.last_gitlab_activity) if activity else None
    redmine_days = activity_days(activity.last_redmine_activity) if activity else None
    if project.archived_at:
        state, label = "archived", "В архиве"
    elif project.is_paused:
        state, label = "paused", "На паузе"
    elif gitlab_days is None and redmine_days is None:
        state, label = "unknown", "Нет данных"
    else:
        # По макету: зелёный <= 3 д., жёлтый <= 7 д., красный > 7 д.
        # Статус определяется худшим из доступных источников.
        worst = max(x for x in (gitlab_days, redmine_days) if x is not None)
        if worst <= project.active_after_days:
            state, label = "working", "Идёт работа"
        elif worst <= project.delayed_after_days:
            state, label = "delayed", "Замедление"
        else:
            state, label = "idle", "Простой"
    total = activity.tasks_total if activity else None
    done = activity.tasks_done if activity else None
    progress = round(min(100, max(0, done / total * 100))) if total and done is not None else None
    return ProjectView(
        id=project.id, workspace_id=project.workspace_id, name=project.name,
        showcase_url=project.showcase_url, gitlab_url=project.gitlab_url,
        redmine_url=project.redmine_url,
        gitlab_token_configured=bool(project.gitlab_token_encrypted),
        redmine_token_configured=bool(project.redmine_token_encrypted),
        sprint_weeks=project.sprint_weeks, active_after_days=project.active_after_days,
        delayed_after_days=project.delayed_after_days, start_date=project.start_date,
        deadline=project.deadline, is_paused=project.is_paused,
        archived_at=project.archived_at, status=state, status_label=label,
        progress_percent=progress, tasks_done=done, tasks_total=total,
        gitlab_inactive_days=gitlab_days, redmine_inactive_days=redmine_days,
        commits_per_day=activity.commits_per_day if activity else None,
        members=[member_view(m, user_map) for m in participants],
        created_at=project.created_at, updated_at=project.updated_at,
    )


def check_activity_thresholds(active: int, delayed: int):
    if delayed <= active:
        raise HTTPException(status_code=422, detail="delayed_after_days must exceed active_after_days")


def write_fields(project: Project, payload: dict):
    for field in ("name", "showcase_url", "gitlab_url", "redmine_url",
                  "sprint_weeks", "active_after_days", "delayed_after_days",
                  "start_date", "deadline"):
        if field in payload:
            value = payload[field]
            setattr(project, field, str(value) if field.endswith("_url") and value is not None else value)
    check_activity_thresholds(project.active_after_days, project.delayed_after_days)
    if project.start_date and project.deadline and project.start_date > project.deadline:
        raise HTTPException(status_code=422, detail="deadline cannot precede start_date")
    for service in ("gitlab", "redmine"):
        token = payload.get(service + "_token")
        if token is not None:
            if not getattr(project, service + "_url"):
                raise HTTPException(status_code=422, detail=f"{service}_url is required with {service}_token")
            setattr(project, service + "_token_encrypted", encrypt_token(token))
        # При удалении URL удаляем и зашифрованный токен.
        if service + "_url" in payload and not getattr(project, service + "_url"):
            setattr(project, service + "_token_encrypted", None)


@router.get("", response_model=ProjectListResponse)
def list_projects(filter: ProjectListFilter = ProjectListFilter.active,
                  db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Для кнопок «Активные», «На паузе», «Архив». counts — счётчики для вкладок."""
    ids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    projects = db.scalars(select(Project).where(or_(Project.owner_id == user.id, Project.id.in_(ids)))
                          .order_by(Project.created_at.desc())).all()
    counts = {"active": 0, "paused": 0, "archived": 0, "all": len(projects)}
    for p in projects:
        counts["archived" if p.archived_at else "paused" if p.is_paused else "active"] += 1
    def matches(p: Project) -> bool:
        return filter == ProjectListFilter.all or (
            (filter == ProjectListFilter.archived and p.archived_at is not None) or
            (filter == ProjectListFilter.paused and p.archived_at is None and p.is_paused) or
            (filter == ProjectListFilter.active and p.archived_at is None and not p.is_paused)
        )
    return ProjectListResponse(items=[project_view(db, p) for p in projects if matches(p)], counts=counts)


@router.post("", status_code=201, response_model=ProjectView)
def create_project(data: ProjectWrite, db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Создание проекта: все настройки берутся из формы «Новый проект»."""
    workspace = Workspace(name=data.name)
    db.add(workspace)
    db.flush()
    project = Project(owner_id=user.id, workspace_id=workspace.id, name=data.name)
    write_fields(project, data.model_dump(exclude_none=True))
    db.add(project)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    db.add(ProjectMember(project_id=project.id, user_id=user.id,
                         email=(user.email or f"{user.id}@local.invalid").lower(), role="owner",
                         joined_at=datetime.now(timezone.utc)))
    db.commit()
    db.refresh(project)
    return project_view(db, project)


@router.get("/{project_id}", response_model=ProjectView)
def get_project(project_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return project_view(db, load_project(db, project_id, user))


@router.patch("/{project_id}", response_model=ProjectView)
def update_project(project_id: UUID, data: ProjectUpdate,
                   db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Настройки: PATCH изменяет только переданные поля; токены НЕ возвращаются."""
    project = load_project(db, project_id, user, write=True)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes:
        if changes["name"] is None:
            raise HTTPException(status_code=422, detail="name cannot be null")
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise HTTPException(status_code=422, detail="name cannot be empty")
    write_fields(project, changes)
    db.commit()
    db.refresh(project)
    return project_view(db, project)


@router.post("/{project_id}/pause", response_model=ProjectView)
def pause_project(project_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user, write=True)
    if project.archived_at:
        raise HTTPException(status_code=409, detail="Restore archived project first")
    project.is_paused = True
    db.commit()
    db.refresh(project)
    return project_view(db, project)


@router.post("/{project_id}/resume", response_model=ProjectView)
def resume_project(project_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user, write=True)
    if project.archived_at:
        raise HTTPException(status_code=409, detail="Restore archived project first")
    project.is_paused = False
    db.commit()
    db.refresh(project)
    return project_view(db, project)


@router.post("/{project_id}/archive", response_model=ProjectView)
def archive_project(project_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user, write=True)
    if not project.archived_at:
        project.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(project)
    return project_view(db, project)


@router.post("/{project_id}/restore", response_model=ProjectView)
def restore_project(project_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user, write=True)
    project.archived_at = None
    db.commit()
    db.refresh(project)
    return project_view(db, project)


@router.post("/{project_id}/members", status_code=201, response_model=ProjectMemberView)
def add_member(project_id: UUID, data: ProjectMemberCreate,
               db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Приглашение по email: реальная доставка письма ещё НЕ реализована."""
    project = load_project(db, project_id, user, write=True)
    if data.role.strip().lower() in {"owner", "владелец"}:
        raise HTTPException(status_code=422, detail="Owner role cannot be assigned")
    person = db.scalar(select(User).where(func.lower(User.email) == data.email))
    if db.scalar(select(ProjectMember).where(ProjectMember.project_id == project.id,
                                             ProjectMember.email == data.email)):
        raise HTTPException(status_code=409, detail="Member already added")
    member = ProjectMember(project_id=project.id, user_id=person.id if person else None,
                           email=data.email, role=data.role,
                           joined_at=datetime.now(timezone.utc) if person else None)
    db.add(member)
    if person and not db.scalar(select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == project.workspace_id, WorkspaceMember.user_id == person.id)):
        db.add(WorkspaceMember(workspace_id=project.workspace_id, user_id=person.id, role="viewer"))
    db.commit()
    db.refresh(member)
    return member_view(member, {person.id: person} if person else {})


@router.delete("/{project_id}/members/{member_id}", status_code=204)
def remove_member(project_id: UUID, member_id: UUID,
                  db: Session = Depends(get_db), user: User = Depends(require_user)):
    project = load_project(db, project_id, user, write=True)
    member = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project.id,
                                                  ProjectMember.id == member_id))
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.user_id == project.owner_id or member.role == "owner":
        raise HTTPException(status_code=403, detail="Cannot remove owner")
    participant_id = member.user_id
    db.delete(member)
    if participant_id:
        ws_member = db.scalar(select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == project.workspace_id,
            WorkspaceMember.user_id == participant_id))
        if ws_member:
            db.delete(ws_member)
    db.commit()
    return Response(status_code=204)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: UUID, confirmation: ConfirmDelete,
                   db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Удаление требует точного имени проекта (модальное окно на макете)."""
    project = load_project(db, project_id, user, write=True)
    if confirmation.name != project.name:
        raise HTTPException(status_code=409, detail="Project name does not match")
    workspace = db.get(Workspace, project.workspace_id)
    # SQL foreign keys Analytics/GitLab/Redmine хранятся в других БД.
    # Здесь удаляется только локальный проект; внешние данные не затрагиваются.
    db.delete(project)
    db.flush()
    db.execute(delete(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id))
    db.delete(workspace)
    db.commit()
    return Response(status_code=204)
