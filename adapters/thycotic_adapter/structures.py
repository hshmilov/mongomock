from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter


class ThycoticUserInstance(UserAdapter):
    domain_id = Field(int, 'Domain ID')
    enabled = Field(bool, 'Enabled')
    is_application_account = Field(bool, 'Application Account')
    login_failures = Field(int, 'Login Failures')
