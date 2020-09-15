import datetime

from axonius.fields import Field
from axonius.users.user_adapter import UserAdapter


class PingoneUserInstance(UserAdapter):
    location = Field(str, 'Location')
    last_modified = Field(datetime.datetime, 'Last Modified')
    active = Field(bool, 'Active')
