from enum import Enum


class AuditCategory(Enum):
    UserManagement = 'settings.users'
    PluginSettings = 'settings.plugins'
    UserSession = 'session'
    Discovery = 'discovery'
    CustomDiscovery = 'custom_discovery'
    ConnectionCustomDiscovery = 'connection_custom_discovery'
    GettingStarted = 'getting_started'
    Adapters = 'adapters'
    Reports = 'reports'
    Enforcements = 'enforcements'
    Tunnel = 'tunnel'
    Dashboard = 'dashboard'
    Instances = 'instances'
    Charts = 'dashboard.charts'


class AuditAction(Enum):
    Login = 'login'
    Logout = 'logout'
    Start = 'start'
    Post = 'post'
    Complete = 'complete'
    StartPhase = 'start_phase'
    CompletePhase = 'complete_phase'
    Failure = 'failure'
    Fetch = 'fetch'
    Clean = 'clean'
    Trigger = 'trigger'
    Download = 'download'
    ChangedPassword = 'changed_password'
    PasswordExpired = 'password_expiration'
    Connected = 'connected'
    Disconnected = 'disconnected'
    Skip = 'skip'
    ChangedName = 'changed_name'
    ChangedPermissions = 'changed_permissions'
    AssignedRole = 'assigned_role'
    TagReimaged = 'tag_reimaged'
    ExportCsv = 'export_csv'
    TagUpdate = 'update_tags'


class AuditType(Enum):
    User = 'user'
    Info = 'info'
    Error = 'error'
