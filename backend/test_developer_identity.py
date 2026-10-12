from uuid import UUID

from analytics_service.app.services.user_identity import (
    get_confirmed_user_mapping,
    get_developer_commits,
)

PROJECT_MAPPING_ID = UUID(
    "ae24008f-9378-4245-ae0e-c91f6b27ae60"
)

GITLAB_USER_ID = 42868272

AUTHOR_EMAIL = "lissena2006@gmail.com"


mapping = get_confirmed_user_mapping(
    PROJECT_MAPPING_ID,
    GITLAB_USER_ID,
)

print("Соответствие пользователей:", mapping)

commits = get_developer_commits(
    PROJECT_MAPPING_ID,
    AUTHOR_EMAIL,
)

print("Количество коммитов:", len(commits))
print(
    "Количество обычных коммитов:",
    sum(not commit["is_merge"] for commit in commits),
)