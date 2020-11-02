import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter


class Project(SmartJsonClass):
    project_id = Field(int, 'ID')
    key = Field(str, 'Key')
    name = Field(str, 'Name')
    public = Field(bool, 'Public')
    project_type = Field(str, 'Type')
    description = Field(str, 'Description')


class User(SmartJsonClass):
    name = Field(str, 'Name')
    email = Field(str, 'Email Address')
    time = Field(datetime.datetime, 'Time')


class Commit(SmartJsonClass):
    commit_id = Field(str, 'ID')
    display_id = Field(str, 'Display ID')
    author = Field(User, 'Author')
    committer = Field(User, 'Committer')
    message = Field(str, 'Message')


class BitbucketDeviceInstance(DeviceAdapter):
    project = Field(Project, 'Project')
    state = Field(str, 'State')
    status_message = Field(str, 'Status Message')
    public = Field(bool, 'Public')
    commits = ListField(Commit, 'Commits')
