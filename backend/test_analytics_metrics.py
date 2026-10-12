
from sqlalchemy import select

from analytics_service.app.database import SessionLocal
from analytics_service.app.models import ProjectMapping
from analytics_service.app.services.metrics_service import (
    calculate_project_metrics,
)


with SessionLocal() as db:
    mapping = db.scalar(
        select(ProjectMapping).where(
            ProjectMapping.redmine_project_id == 1,
            ProjectMapping.gitlab_project_id == 87303510,
        )
    )

    if mapping is None:
        raise ValueError("Project mapping not found")

    project_mapping_id = mapping.id

result = calculate_project_metrics(project_mapping_id)

print("Аналитические метрики рассчитаны:")

for name, value in result.items():
    print(f"{name}: {value}")
