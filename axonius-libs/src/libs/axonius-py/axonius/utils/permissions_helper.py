from enum import Enum
from typing import NamedTuple

from axonius.consts.gui_consts import PREDEFINED_ROLE_ADMIN, PREDEFINED_ROLE_OWNER, PREDEFINED_FIELD, IS_AXONIUS_ROLE


# Represent the possible aspects of the system the user might access


class PermissionCategory(Enum):
    Settings = 'settings'
    Users = 'users'
    Roles = 'roles'
    Audit = 'audit'
    Dashboard = 'dashboard'
    Spaces = 'spaces'
    Charts = 'charts'
    DevicesAssets = 'devices_assets'
    UsersAssets = 'users_assets'
    SavedQueries = 'saved_queries'
    Instances = 'instances'
    Adapters = 'adapters'
    Connections = 'connections'
    Enforcements = 'enforcements'
    Tasks = 'tasks'
    Reports = 'reports'
    Compliance = 'compliance'

    @classmethod
    def has_value(cls, value):
        # pylint: disable=no-member
        return value in cls._value2member_map_


# Represent actions of users in the system
class PermissionAction(Enum):
    View = 'get'
    Add = 'put'
    Update = 'post'
    Delete = 'delete'
    GetUsersAndRoles = 'get_users_and_roles'
    ResetApiKey = 'reset_api_key'
    RunManualDiscovery = 'run_manual_discovery'
    Run = 'run'


# Represent a permission in the system
class PermissionValue(NamedTuple):
    Action: PermissionAction
    Category: PermissionCategory
    Section: PermissionCategory

    @classmethod
    def get(cls, action: PermissionAction = None,
            category: PermissionCategory = None,
            section: PermissionCategory = None):
        if category and section:
            return PermissionValue(action, category, section)
        if category:
            return PermissionValue(action, category, None)
        return PermissionAction(action, None, None)


def get_permissions_structure(default_permission: bool) -> dict:
    return {
        PermissionCategory.Settings: {
            PermissionAction.View: default_permission,
            PermissionAction.GetUsersAndRoles: default_permission,
            PermissionCategory.Users: {
                PermissionAction.Add: default_permission,
                PermissionAction.Update: default_permission,
                PermissionAction.Delete: default_permission,
            },
            PermissionCategory.Roles: {
                PermissionAction.Add: default_permission,
                PermissionAction.Update: default_permission,
                PermissionAction.Delete: default_permission,
            },
            PermissionAction.ResetApiKey: default_permission,
            PermissionAction.Update: default_permission,
            PermissionAction.RunManualDiscovery: default_permission,
            PermissionCategory.Audit: {
                PermissionAction.View: default_permission,
            },
        },
        PermissionCategory.Dashboard: {
            PermissionAction.View: default_permission,
            PermissionCategory.Charts: {
                PermissionAction.Delete: default_permission,
                PermissionAction.Add: default_permission,
                PermissionAction.Update: default_permission,
            },
            PermissionCategory.Spaces: {
                PermissionAction.Add: default_permission,
                PermissionAction.Delete: default_permission,
            }
        },
        PermissionCategory.DevicesAssets: {
            PermissionAction.View: default_permission,
            PermissionAction.Update: default_permission,
            PermissionCategory.SavedQueries: {
                PermissionAction.Run: default_permission,
                PermissionAction.Update: default_permission,
                PermissionAction.Delete: default_permission,
                PermissionAction.Add: default_permission,
            },
        },
        PermissionCategory.UsersAssets: {
            PermissionAction.View: default_permission,
            PermissionAction.Update: default_permission,
            PermissionCategory.SavedQueries: {
                PermissionAction.Run: default_permission,
                PermissionAction.Update: default_permission,
                PermissionAction.Delete: default_permission,
                PermissionAction.Add: default_permission,
            },
        },
        PermissionCategory.Reports: {
            PermissionAction.View: default_permission,
            PermissionAction.Add: default_permission,
            PermissionAction.Update: default_permission,
            PermissionAction.Delete: default_permission,
        },
        PermissionCategory.Instances: {
            PermissionAction.View: default_permission,
            PermissionAction.Update: default_permission,
        },
        PermissionCategory.Adapters: {
            PermissionAction.View: default_permission,
            PermissionCategory.Connections: {
                PermissionAction.Add: default_permission,
                PermissionAction.Update: default_permission,
                PermissionAction.Delete: default_permission,
            },
            PermissionAction.Update: default_permission,
        },
        PermissionCategory.Enforcements: {
            PermissionAction.View: default_permission,
            PermissionAction.Update: default_permission,
            PermissionAction.Add: default_permission,
            PermissionCategory.Tasks: {
                PermissionAction.View: default_permission,
            },
            PermissionAction.Delete: default_permission,
            PermissionAction.Run: default_permission,
        },
        PermissionCategory.Compliance: {
            PermissionAction.View: default_permission,
        },
    }


def serialize_db_permissions(permissions):
    """
    Converts pythonic permissions to DB-like types
    """
    serialized_permissions = {}
    for k, v in permissions.items():
        if k in PermissionCategory:
            serialized_permissions[k.value] = serialize_db_permissions(v)
        else:
            serialized_permissions[k.value] = v
    return serialized_permissions


def deserialize_db_permissions(permissions):
    """
    Converts DB-like permissions to pythonic types
    """
    deserialized_permissions = {}
    for k, v in permissions.items():
        if PermissionCategory.has_value(k):
            key = PermissionCategory(k)
            deserialized_permissions[key] = deserialize_db_permissions(v)
        else:
            key = PermissionAction(k)
            deserialized_permissions[key] = v
    return deserialized_permissions


def get_admin_permissions():
    return serialize_db_permissions(get_permissions_structure(True))


def get_viewer_permissions():
    viewer_permissions = get_permissions_structure(False)
    viewer_permissions[PermissionCategory.Dashboard][PermissionAction.View] = True
    viewer_permissions[PermissionCategory.DevicesAssets][PermissionAction.View] = True
    viewer_permissions[PermissionCategory.UsersAssets][PermissionAction.View] = True
    viewer_permissions[PermissionCategory.Reports][PermissionAction.View] = True
    viewer_permissions[PermissionCategory.Instances][PermissionAction.View] = True
    viewer_permissions[PermissionCategory.Adapters][PermissionAction.View] = True
    viewer_permissions[PermissionCategory.Enforcements][PermissionAction.View] = True
    viewer_permissions[PermissionCategory.Compliance][PermissionAction.View] = True

    return serialize_db_permissions(viewer_permissions)


def get_restricted_permissions():
    restricted_permissions = get_permissions_structure(False)
    restricted_permissions[PermissionCategory.Dashboard][PermissionAction.View] = True

    return serialize_db_permissions(restricted_permissions)


def is_role_admin(user):
    role_name = user.get('role_name')
    predefined = user.get(PREDEFINED_FIELD)
    return role_name in [PREDEFINED_ROLE_ADMIN, PREDEFINED_ROLE_OWNER] and predefined


def is_axonius_role(user):
    is_axonius = user.get(IS_AXONIUS_ROLE)
    predefined = user.get(PREDEFINED_FIELD)
    return is_axonius and predefined
