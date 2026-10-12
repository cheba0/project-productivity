from uuid import UUID

from analytics_service.app.services.developer_metrics import (
    get_developer_metrics,
)

result = get_developer_metrics(
    project_mapping_id=UUID(
        "ae24008f-9378-4245-ae0e-c91f6b27ae60"
    ),
    gitlab_user_id=42868272,
    author_email="lissena2006@gmail.com",
)

print("Персональная аналитика разработчика:")

for key, value in result.items():
    print(f"{key}: {value}")