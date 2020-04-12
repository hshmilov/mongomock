from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter


class Permission(SmartJsonClass):
    # equivalent of axonius.utils.gui_helpers.Permission
    type = Field(str, 'Permission Type')
    level = Field(str, 'Permission Level')


class SystemUser(UserAdapter):
    source = Field(str, 'User Source')
    role_name = Field(str, 'Role Name')
    permissions = ListField(Permission, 'Permissions')
