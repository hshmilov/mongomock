from axonius.fields import Field, ListField, JsonStringFormat
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.parsing import format_ip, format_ip_raw


class Project(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')


class Group(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')


class GitLabUserInstance(UserAdapter):
    web_url = Field(str, 'Web URL')
    location = Field(str, 'Location')
    skype = Field(str, 'Skype')
    linkedin = Field(str, 'Linkedin')
    twitter = Field(str, 'Twitter')
    note = Field(str, 'Note')
    is_private = Field(bool, 'Private')
    current_ip = Field(str, 'Current Sign In IP', converter=format_ip, json_format=JsonStringFormat.ip)
    current_ip_raw = Field(str,
                           description='Number representation of the Public IP, useful for filtering by range',
                           converter=format_ip_raw,
                           hidden=True)
    last_ip = Field(str, 'Last Sign In IP', converter=format_ip, json_format=JsonStringFormat.ip)
    last_ip_raw = Field(str,
                        description='Number representation of the Public IP, useful for filtering by range',
                        converter=format_ip_raw,
                        hidden=True)
    projects = ListField(Project, 'Projects')
    user_groups = ListField(Group, 'User Groups')
