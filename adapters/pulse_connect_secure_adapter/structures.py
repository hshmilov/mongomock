from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter


class PulseConnectSecureUserInstance(UserAdapter):
    agent_type = Field(str, 'Agent Type')
