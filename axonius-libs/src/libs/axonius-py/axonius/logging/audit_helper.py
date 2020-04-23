from enum import Enum


class AuditCategory(Enum):
    UserSession = 'session'
    Discovery = 'discovery'
    GettingStarted = 'getting_started'
    Adapters = 'adapters'
    Reports = 'reports'
    Enforcements = 'enforcements'


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


class AuditType(Enum):
    User = 'user'
    Info = 'info'
    Error = 'error'
