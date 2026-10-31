"""Живые показатели ТОЛЬКО из GitLab API v4 и Redmine REST API.

Не использует тестовые цифры из Figma. Для GitLab URL ожидается адрес
проекта .../group/repo, для Redmine .../projects/identifier.
Ошибки upstream возвращаются как 502/503, а не как нулевые показатели.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote, urlparse
import ipaddress
import os
import socket

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

MAX_PAGES = 30  # ограничение, чтобы запросы не перегружали сервер
PAGE_SIZE = 100


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _date(value):
    dt = _parse_dt(value)
    return dt.date() if dt else None


def _host_is_public(host):
    if not host or host.lower() in ('localhost', 'localhost.localdomain'):
        return False
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)
    except (OSError, ValueError):
        return False


def _project_endpoint(url, service):
    parsed = urlparse(url or '')
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise HTTPException(422, f'{service}_url must be a public HTTPS project URL')
    # На сервере для внутренних корпоративных API можно явно разрешить домены.
    allowed = {s.strip().lower() for s in os.getenv('PROJECT_API_ALLOWED_HOSTS', '').split(',') if s.strip()}
    if parsed.hostname.lower() not in allowed and not _host_is_public(parsed.hostname):
        raise HTTPException(422, f'{service}_url host is not allowed')
    path = parsed.path.rstrip('/')
    if service == 'gitlab':
        if '/-/' in path:
            path = path.split('/-/')[0]
        path = path.removesuffix('.git')
        if not path.strip('/'):
            raise HTTPException(422, 'GitLab project path missing')
        # Поддерживает GitLab, установленный в подпапке: API base задаётся отдельно.
        api_base = os.getenv('PROJECT_GITLAB_API_BASE')
        if api_base:
            base = api_base.rstrip('/')
        else:
            base = f'{parsed.scheme}://{parsed.netloc}/api/v4'
        return base, quote(path.lstrip('/'), safe='')
    if '/projects/' not in path:
        raise HTTPException(422, 'Redmine URL must contain /projects/{identifier}')
    root, identifier = path.rsplit('/projects/', 1)
    identifier = identifier.split('/')[0]
    if not identifier:
        raise HTTPException(422, 'Redmine project identifier missing')
    return f'{parsed.scheme}://{parsed.netloc}{root}', identifier


def _token(encrypted):
    if not encrypted:
        raise HTTPException(409, 'Integration token not configured')
    key = os.getenv('PROJECT_TOKEN_ENCRYPTION_KEY')
    if not key:
        raise HTTPException(503, 'PROJECT_TOKEN_ENCRYPTION_KEY missing')
    try:
        return Fernet(key.encode()).decrypt(encrypted).decode()
    except (InvalidToken, ValueError, TypeError):
        raise HTTPException(503, 'Cannot decrypt integration token')


class Api:
    def __init__(self, base, headers):
        self.base = base.rstrip('/')
        self.headers = headers

    def get(self, path, params=None):
        # follow_redirects=False: токены никогда не пересылаются на redirect-хост.
        try:
            with httpx.Client(timeout=12.0, follow_redirects=False, trust_env=False) as client:
                response = client.get(self.base + path, params=params, headers=self.headers)
            if response.status_code in (401, 403):
                raise HTTPException(502, 'Integration API rejected credentials or permissions')
            if response.status_code >= 300:
                raise HTTPException(502, f'Integration API returned HTTP {response.status_code}')
            return response.json()
        except httpx.HTTPError:
            raise HTTPException(502, 'Integration API unavailable')
        except ValueError:
            raise HTTPException(502, 'Integration API returned invalid JSON')

    def pages(self, path, params=None):
        result = []
        params = dict(params or {})
        for page in range(1, MAX_PAGES + 1):
            payload = self.get(path, {**params, 'page': page, 'per_page': PAGE_SIZE,
                                      'limit': PAGE_SIZE, 'offset': (page - 1) * PAGE_SIZE})
            if isinstance(payload, list):
                chunk = payload
            elif isinstance(payload, dict):
                chunk = next((payload[key] for key in ('issues', 'time_entries', 'users') if isinstance(payload.get(key), list)), None)
                if chunk is None:
                    raise HTTPException(502, 'Unexpected API response structure')
            else:
                raise HTTPException(502, 'Unexpected API response structure')
            result.extend(chunk)
            if len(chunk) < PAGE_SIZE:
                return result
        raise HTTPException(503, 'Integration has more than 3000 records; narrow date range')


def fetch(project, start: date, end: date):
    """Один вызов получает живые данные; никаких сохранённых/фиктивных метрик."""
    if start > end:
        raise HTTPException(422, 'start must be <= end')
    if (end - start).days > 366:
        raise HTTPException(422, 'Maximum period is 366 days')

    if not (project.gitlab_url and project.gitlab_token_encrypted) and not (project.redmine_url and project.redmine_token_encrypted):
        raise HTTPException(409, 'At least one integration URL and token required')
    commits, issues, entries = [], [], []
    sources = {'gitlab': 'not_configured', 'redmine': 'not_configured'}
    if project.gitlab_url and project.gitlab_token_encrypted:
        git_base, git_id = _project_endpoint(project.gitlab_url, 'gitlab')
        git = Api(git_base, {'PRIVATE-TOKEN': _token(project.gitlab_token_encrypted)})
        commits = git.pages(f'/projects/{git_id}/repository/commits', {
            'since': start.isoformat() + 'T00:00:00Z',
            'until': end.isoformat() + 'T23:59:59Z', 'all': 'true',
        })
        sources['gitlab'] = 'live'
    if project.redmine_url and project.redmine_token_encrypted:
        red_base, red_id = _project_endpoint(project.redmine_url, 'redmine')
        red = Api(red_base, {'X-Redmine-API-Key': _token(project.redmine_token_encrypted)})
        issues = red.pages('/issues.json', {'project_id': red_id, 'status_id': '*'})
        entries = red.pages('/time_entries.json', {'project_id': red_id,
                            'from': start.isoformat(), 'to': end.isoformat()})
        sources['redmine'] = 'live'
    return {'commits': commits, 'issues': issues, 'entries': entries,
            'period': {'start': start.isoformat(), 'end': end.isoformat()},
            'sources': sources}

def sprint_dates(project, number, today=None):
    if not project.start_date:
        raise HTTPException(409, 'Project start_date required to calculate sprints')
    if number < 1:
        raise HTTPException(422, 'sprint must be >= 1')
    duration = timedelta(weeks=project.sprint_weeks)
    start = project.start_date + (number - 1) * duration
    end = start + duration - timedelta(days=1)
    if project.deadline:
        end = min(end, project.deadline)
    if end < start:
        raise HTTPException(404, 'Sprint outside project dates')
    return start, end


def sprint_list(project, today=None):
    if not project.start_date:
        return {'items': [], 'current_sprint': None}
    end = project.deadline or (today or date.today())
    if end < project.start_date:
        return {'items': [], 'current_sprint': None}
    span = project.sprint_weeks * 7
    count = min(300, (end - project.start_date).days // span + 1)
    items = []
    current = None
    now = today or date.today()
    for number in range(1, count + 1):
        start, finish = sprint_dates(project, number)
        if start <= now <= finish:
            current = number
        items.append({'number': number, 'start': start.isoformat(), 'end': finish.isoformat()})
    return {'items': items, 'current_sprint': current}


def _hours(value):
    return round(float(value or 0), 2)


def compute(data, members, users, start, end, profiles=None, *,
            active_after_days=3, delayed_after_days=7, as_of=None):
    """Нормализованный ответ для всех экранов, исключительно из upstream JSON.

    Redmine spent_on/time_entries — фактические часы; estimated_hours — план.
    Нет данных об оценке -> planned_hours=null, а не 0.
    """
    commits, issues, entries = data['commits'], data['issues'], data['entries']
    days = defaultdict(lambda: {'gitlab_commits': 0, 'redmine_updates': 0, 'redmine_hours': 0.0})
    git_by_email = defaultdict(list)
    git_by_name = defaultdict(list)
    for commit in commits:
        when = _date(commit.get('committed_date') or commit.get('created_at'))
        if not when or not start <= when <= end:
            continue
        days[when.isoformat()]['gitlab_commits'] += 1
        email = (commit.get('author_email') or '').strip().lower()
        name = (commit.get('author_name') or '').strip().casefold()
        if email:
            git_by_email[email].append(commit)
        if name:
            git_by_name[name].append(commit)
    red_by_id = defaultdict(list)
    for entry in entries:
        when = entry.get('spent_on')
        if not when or not start.isoformat() <= when <= end.isoformat():
            continue
        days[when]['redmine_updates'] += 1
        days[when]['redmine_hours'] += _hours(entry.get('hours'))
        red_by_id[str((entry.get('user') or {}).get('id'))].append(entry)
    entry_hours_by_issue = defaultdict(float)
    for entry in entries:
        issue_id = (entry.get('issue') or {}).get('id')
        if issue_id is not None:
            entry_hours_by_issue[str(issue_id)] += float(entry.get('hours') or 0)
    tasks = []
    for issue in issues:
        due = issue.get('due_date')
        created = (issue.get('start_date') or '')
        # Задача попадает в период при пересечении интервала start_date/due_date.
        if created and created > end.isoformat():
            continue
        if due and due < start.isoformat():
            continue
        assigned = issue.get('assigned_to') or {}
        status = issue.get('status') or {}
        status_name = status.get('name') or ''
        closed = bool(issue.get('closed_on')) or status_name.lower() in ('closed', 'закрыта', 'resolved', 'решена')
        tasks.append({'id': issue.get('id'), 'title': issue.get('subject'),
                      'status': status_name, 'done': closed,
                      'assigned_to': assigned.get('id'),
                      'estimated_hours': issue.get('estimated_hours'),
                      'spent_hours': round(entry_hours_by_issue.get(str(issue.get('id')), 0), 2),
                      'start_date': created or None, 'due_date': due})
    total = len(tasks)
    done = sum(t['done'] for t in tasks)
    total_planned = sum(_hours(t['estimated_hours']) for t in tasks if t['estimated_hours'] is not None)
    total_actual = sum(_hours(t['spent_hours']) for t in tasks)
    estimated_count = sum(t['estimated_hours'] is not None for t in tasks)
    quality = {'normal': 0, 'warning': 0, 'error': 0, 'unplanned': 0}
    for task in tasks:
        estimate = task['estimated_hours']
        if estimate is None or float(estimate) == 0:
            quality['unplanned'] += 1
        else:
            deviation = (task['spent_hours'] - float(estimate)) / float(estimate)
            quality['normal' if deviation <= 0.1 else 'warning' if deviation <= 0.2 else 'error'] += 1
    # Ignore missing timestamps rather than comparing None with datetime.
    last_git = max((dt for c in commits
                    if (dt := _parse_dt(c.get('committed_date') or c.get('created_at')))), default=None)
    last_red = max((
        [dt for i in issues if (dt := _parse_dt(i.get('updated_on')))]
        + [dt for e in entries
           if (dt := _parse_dt(e.get('created_on') or e.get('spent_on')))]
    ), default=None)

    profiles = profiles or {}
    today = (as_of or datetime.now(timezone.utc)).date()

    def inactivity(last):
        return max(0, (today - last.date()).days) if last else None

    def tier(days):
        if days is None:
            return None
        return ('working' if days <= active_after_days else
                'delayed' if days <= delayed_after_days else 'idle')

    students = []
    for member in members:
        user = users.get(member.user_id)
        profile = profiles.get(member.id)
        name = user.name if user else None
        email = member.email.strip().lower()
        # Email must be explicitly stored in the profile or match the
        # authenticated TPU member email; never join users by display name.
        git_email = ((getattr(profile, 'gitlab_email', None) or email)
                     .strip().lower())
        matched = git_by_email.get(git_email, [])
        git_last = max(
            (dt for c in matched
             if (dt := _parse_dt(c.get('committed_date') or c.get('created_at')))),
            default=None,
        )
        red_id = getattr(profile, 'redmine_user_id', None)
        red_entries = red_by_id.get(str(red_id), []) if red_id is not None else []
        assigned = ([t for t in tasks if str(t['assigned_to']) == str(red_id)]
                    if red_id is not None else [])
        plan_values = [float(t['estimated_hours']) for t in assigned
                       if t['estimated_hours'] is not None]
        planned = round(sum(plan_values), 2) if plan_values else None
        actual = (round(sum(_hours(e.get('hours')) for e in red_entries), 2)
                  if red_id is not None else None)
        red_last = max(
            (dt for e in red_entries
             if (dt := _parse_dt(e.get('created_on') or e.get('spent_on')))),
            default=None,
        )
        git_days, red_days = inactivity(git_last), inactivity(red_last)
        known_tiers = [v for v in (tier(git_days), tier(red_days)) if v]
        activity_status = (
            'unknown' if not known_tiers else
            'partial' if len(set(known_tiers)) > 1 else
            known_tiers[0]
        )
        students.append({
            'member_id': str(member.id), 'name': name, 'email': email,
            'role': member.role, 'gitlab_commits': len(matched),
            'redmine_user_id': red_id,
            'redmine_entries': len(red_entries) if red_id is not None else None,
            'redmine_hours': actual, 'actual_hours': actual,
            'planned_hours': planned,
            'hours_deviation': round(actual - planned, 2)
                if actual is not None and planned is not None else None,
            'hours_deviation_percent': round((actual - planned) / planned * 100, 1)
                if actual is not None and planned is not None and planned > 0 else None,
            'tasks_total': len(assigned) if red_id is not None else None,
            'tasks_done': sum(t['done'] for t in assigned) if red_id is not None else None,
            'tasks_in_progress': sum(not t['done'] for t in assigned)
                if red_id is not None else None,
            'last_gitlab_activity': git_last,
            'last_redmine_activity': red_last,
            'gitlab_inactive_days': git_days,
            'redmine_inactive_days': red_days,
            'activity_status': activity_status,
            'activity_at': max((v for v in (git_last, red_last) if v), default=None),
        })
    return {
        'period': data['period'], 'sources': data['sources'],
        'summary': {'tasks_total': total, 'tasks_done': done, 'tasks_in_progress': total - done,
                    'progress_percent': round(done / total * 100) if total else None,
                    'commits': sum(x['gitlab_commits'] for x in days.values()),
                    'redmine_time_entries': len(entries),
                    'actual_hours': round(total_actual, 2),
                    'planned_hours': round(total_planned, 2) if estimated_count else None,
                    'last_gitlab_activity': last_git, 'last_redmine_activity': last_red},
        'planning_quality': {'counts': quality, 'total': total,
                             'percentages': {k: round(v / total * 100, 1) if total else None for k, v in quality.items()}},
        'tasks': tasks, 'students': students,
        'daily_activity': [{'date': (start + timedelta(days=n)).isoformat(),
                            **days[(start + timedelta(days=n)).isoformat()]}
                           for n in range((end - start).days + 1)],
    }
