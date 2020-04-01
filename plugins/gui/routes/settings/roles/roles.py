import logging

from flask import (jsonify,
                   request)

from axonius.consts.gui_consts import (PREDEFINED_ROLE_ADMIN,
                                       PREDEFINED_ROLE_READONLY,
                                       PREDEFINED_ROLE_RESTRICTED,
                                       PREDEFINED_FIELD)
from axonius.plugin_base import return_error
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType)
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.filter_utils import filter_archived
from gui.logic.routing_helper import gui_add_rule_logged_in
# pylint: disable=no-member,no-else-return

logger = logging.getLogger(f'axonius.{__name__}')


class Roles:

    def _add_default_roles(self):
        if self._roles_collection.find_one({'name': PREDEFINED_ROLE_ADMIN}) is None:
            # Admin role doesn't exists - let's create it
            self._roles_collection.insert_one({
                'name': PREDEFINED_ROLE_ADMIN, PREDEFINED_FIELD: True, 'permissions': {
                    p.name: PermissionLevel.ReadWrite.name for p in PermissionType
                }
            })
        if self._roles_collection.find_one({'name': PREDEFINED_ROLE_READONLY}) is None:
            # Read-only role doesn't exists - let's create it
            self._roles_collection.insert_one({
                'name': PREDEFINED_ROLE_READONLY, PREDEFINED_FIELD: True, 'permissions': {
                    p.name: PermissionLevel.ReadOnly.name for p in PermissionType
                }
            })
        if self._roles_collection.find_one({'name': PREDEFINED_ROLE_RESTRICTED}) is None:
            # Restricted role doesn't exists - let's create it. Everything restricted except the Dashboard.
            permissions = {
                p.name: PermissionLevel.Restricted.name for p in PermissionType
            }
            permissions[PermissionType.Dashboard.name] = PermissionLevel.ReadOnly.name
            self._roles_collection.insert_one({
                'name': PREDEFINED_ROLE_RESTRICTED, PREDEFINED_FIELD: True, 'permissions': permissions
            })

    @gui_add_rule_logged_in('roles', methods=['GET', 'PUT', 'POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Settings, PermissionLevel.ReadWrite)})
    def roles(self):
        """
        Service for getting the list of all roles from the DB or creating new roles.
        Roles' names serve as their unique keys

        :return: GET list of roles with their set of permissions
        """
        return self._roles()

    def _roles(self):
        # restricted roles that cannot be edited/deleted by this endpoint.
        restricted_roles = ['Admin']
        if request.method == 'GET':
            return jsonify(
                [beautify_db_entry(entry) for entry in self._roles_collection.find(filter_archived())])

        role_data = self.get_request_data_as_object()
        if 'name' not in role_data:
            logger.error('Name is required for saving a new role')
            return return_error('Name is required for saving a new role', 400)

        match_role = {
            'name': role_data['name']
        }
        if role_data['name'] in restricted_roles:
            logger.error(f'Cannot edit {role_data["name"]} role')
            return return_error(f'Cannot edit {role_data["name"]} role', 400)
        existing_role = self._roles_collection.find_one(filter_archived(match_role))
        if request.method != 'PUT' and not existing_role:
            logger.error(f'Role by the name {role_data["name"]} was not found')
            return return_error(f'Role by the name {role_data["name"]} was not found', 400)
        elif request.method == 'PUT' and existing_role:
            logger.error(f'Role by the name {role_data["name"]} already exists')
            return return_error(f'Role by the name {role_data["name"]} already exists', 400)

        match_user_role = {
            'role_name': role_data['name']
        }
        if request.method == 'DELETE':
            self._roles_collection.update_one(match_role, {
                '$set': {
                    'archived': True
                }
            })
            self._users_collection.update_many(match_user_role, {
                '$set': {
                    'role_name': ''
                }
            })
        else:
            # Handling 'PUT' and 'POST' similarly - new role may replace an existing, archived one
            self._roles_collection.replace_one(match_role, role_data, upsert=True)
            self._users_collection.update_many(match_user_role, {
                '$set': {
                    'permissions': role_data['permissions']
                }
            })
        return ''

    @gui_add_rule_logged_in('roles/default', methods=['GET', 'POST'],
                            required_permissions={Permission(PermissionType.Settings, PermissionLevel.ReadWrite)})
    def roles_default(self):
        """
        Receives a name of a role that will be assigned by default to every external user created

        :return:
        """
        return self._roles_default()

    def _roles_default(self):
        """
        Receives a name of a role that will be assigned by default to every external user created

        :return:
        """
        if request.method == 'GET':
            config_doc = self._users_config_collection.find_one({})
            if not config_doc or 'external_default_role' not in config_doc:
                return ''
            return jsonify(config_doc['external_default_role'])

        # Handle POST, the only option left
        default_role_data = self.get_request_data_as_object()
        if not default_role_data.get('name'):
            logger.error('Role name is required in order to set it as a default')
            return return_error('Role name is required in order to set it as a default')
        if self._roles_collection.find_one(filter_archived(default_role_data)) is None:
            logger.error(f'Role {default_role_data["name"]} was not found and cannot be default')
            return return_error(f'Role {default_role_data["name"]} was not found and cannot be default')
        self._users_config_collection.replace_one({}, {
            'external_default_role': default_role_data['name']
        }, upsert=True)
        return ''
