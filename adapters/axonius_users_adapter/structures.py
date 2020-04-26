from datetime import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.permissions_helper import PermissionAction, PermissionCategory


class PermissionV2(SmartJsonClass):
    category = Field(str, 'Category', enum=PermissionCategory)
    # Note: regarding the enum, this is not a mistake, but probably not separated yet
    section = Field(str, 'Section', enum=PermissionCategory)
    action = Field(str, 'Action', enum=PermissionAction)
    is_permitted = Field(bool, 'Is Permitted')


class Role(SmartJsonClass):
    uuid = Field(str, 'UUID')
    name = Field(str, 'Name')
    date_fetched = Field(datetime, 'Date Fetched')
    predefined = Field(bool, 'Is Predefined')
    permissions = ListField(PermissionV2, 'Permissions')


class PermissionV1(SmartJsonClass):
    # equivalent of axonius.utils.gui_helpers.Permission
    type = Field(str, 'Permission Type')
    level = Field(str, 'Permission Level')


class SystemUser(UserAdapter):
    source = Field(str, 'User Source')

    # permissions (pre 3.3)
    role_name = Field(str, 'Role Name')
    permissions = ListField(PermissionV1, 'Permissions')

    # roles (post 3.3)
    role = Field(Role, 'Role')
