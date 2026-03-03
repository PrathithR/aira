import enum


class IntegrationProvider(str, enum.Enum):
    GOOGLE = "google"
    OUTLOOK = "outlook"
    SLACK = "slack"
    NOTION = "notion"
    GITHUB = "github"


class AuthType(str, enum.Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    USER_PWD = "user_pwd"
    WEBHOOK = "webhook"


class IntegrationStatus(str, enum.Enum):
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    REVOKED = "revoked"


class CredentialStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    NEEDS_REFRESH = "needs_refresh"
    REVOKED = "revoked"


class TaskPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"