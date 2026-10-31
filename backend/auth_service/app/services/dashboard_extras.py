"""Read-only chart data derived from cached Redmine tasks and time entries.

Sprint estimates are attributed by task start_date; actual hours by spent_on.
This is not a historical snapshot of sprint planning decisions.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from auth_service.app.live_metrics import sprint_dates


def _day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _num(value):
    if value is None:
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (TypeError, ValueError, InvalidOperation):
        return None


def sprint_hours(data, project, start, end):
    if not project.start_date:
        return {"available": False, "reason": "project_start_date_missing",
                "plan_basis": "task_start_date", "items": []}
    if start > end:
        raise ValueError("Invalid range")
    ready = data.get("sources", {}).get("redmine") not in (None, "not_configured")
    first = max(start, project.start_date)
    last = min(end, project.deadline) if project.deadline else end
    result = {"available": ready,
              "reason": None if ready else "redmine_not_configured",
              "plan_basis": "task_start_date", "items": [],
              "unallocated_plan_hours": None, "unallocated_estimated_tasks": 0}
    if first > last:
        return result
    span = project.sprint_weeks * 7
    low = (first - project.start_date).days // span + 1
    high = (last - project.start_date).days // span + 1
    if high - low > 299:
        raise ValueError("Too many sprints")
    plans, actuals, counts, spent_counts = {}, {}, {}, {}
    unallocated = Decimal(0)
    for task in data.get("issues", []):
        estimate = _num(task.get("estimated_hours"))
        if estimate is None:
            continue
        day = _day(task.get("start_date"))
        if day is None:
            unallocated += estimate
            result["unallocated_estimated_tasks"] += 1
            continue
        if not first <= day <= last:
            continue
        idx = (day - project.start_date).days // span + 1
        plans[idx] = plans.get(idx, Decimal(0)) + estimate
        counts[idx] = counts.get(idx, 0) + 1
    for entry in data.get("entries", []):
        day, hours = _day(entry.get("spent_on")), _num(entry.get("hours"))
        if day is None or hours is None or not first <= day <= last:
            continue
        idx = (day - project.start_date).days // span + 1
        actuals[idx] = actuals.get(idx, Decimal(0)) + hours
        spent_counts[idx] = spent_counts.get(idx, 0) + 1
    for idx in range(low, high + 1):
        a, b = sprint_dates(project, idx)
        plan = plans.get(idx)
        actual = actuals.get(idx, Decimal(0)) if ready else None
        result["items"].append({
            "sprint": idx, "start": a.isoformat(), "end": b.isoformat(),
            "visible_start": max(a, first).isoformat(),
            "visible_end": min(b, last).isoformat(),
            "partial_period": a < first or b > last,
            "planned_hours": round(float(plan), 2) if plan is not None else None,
            "actual_hours": round(float(actual), 2) if actual is not None else None,
            "deviation_hours": round(float(actual - plan), 2)
                if plan is not None and actual is not None else None,
            "estimated_tasks": counts.get(idx, 0),
            "time_entries": spent_counts.get(idx, 0) if ready else None,
        })
    if result["unallocated_estimated_tasks"]:
        result["unallocated_plan_hours"] = round(float(unallocated), 2)
    return result


def upcoming_deadlines(data, *, today=None, days=14, limit=25):
    if not 1 <= days <= 365 or not 1 <= limit <= 100:
        raise ValueError("Invalid limit")
    today = today or date.today()
    ready = data.get("sources", {}).get("redmine") not in (None, "not_configured")
    known = unknown = 0
    rows = []
    for task in data.get("issues", []):
        status = ((task.get("status") or {}).get("name") or "").strip()
        if task.get("closed_on") or status.lower() in {"closed", "resolved", "закрыта", "решена"}:
            continue
        due = _day(task.get("due_date"))
        if due is None:
            unknown += 1
            continue
        known += 1
        if due > today + timedelta(days=days):
            continue
        days_left = (due - today).days
        rows.append({
            "id": task.get("id"), "title": task.get("subject"), "status": status,
            "due_date": due.isoformat(), "days_remaining": days_left,
            "overdue": days_left < 0,
            "assigned_to": (task.get("assigned_to") or {}).get("id"),
            "estimated_hours": task.get("estimated_hours"),
        })
    rows.sort(key=lambda row: (row["due_date"], str(row["id"])))
    available = ready and known > 0
    return {
        "available": available,
        "reason": None if available else "redmine_not_configured" if not ready
                  else "no_due_dates_in_source",
        "as_of": today.isoformat(), "window_days": days,
        "items": rows[:limit], "total_matching": len(rows),
        "known_due_date_tasks": known, "open_tasks_without_due_date": unknown,
    }
