from enum import Enum


class AuditCategory(Enum):
    UserManagement = 'settings.users'
    UserSession = 'session'
    Discovery = 'discovery'
    CustomDiscovery = 'custom_discovery'
    GettingStarted = 'getting_started'
    Adapters = 'adapters'
    Reports = 'reports'
    Enforcements = 'enforcements'
    Dashboard = 'dashboard'
    Instances = 'instances'


class AuditAction(Enum):
    Login = 'login'
    Logout = 'logout'
    Start = 'start'
    Complete = 'complete'
    StartPhase = 'start_phase'
    CompletePhase = 'complete_phase'
    Failure = 'failure'
    Fetch = 'fetch'
    Clean = 'clean'
    Trigger = 'trigger'
    Download = 'download'
    ChangedPassword = 'changed_password'
    ChangedName = 'changed_name'
    ChangedPermissions = 'changed_permissions'
    AssignedRole = 'assigned_role'
    TagReimaged = 'tag_reimaged'


class AuditType(Enum):
    User = 'user'
    Info = 'info'
    Error = 'error'
