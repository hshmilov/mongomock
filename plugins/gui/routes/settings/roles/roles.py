import logging
import json
from flask import (jsonify)
from bson import ObjectId

from axonius.plugin_base import return_error
from axonius.consts.gui_consts import PREDEFINED_FIELD, IS_AXONIUS_ROLE, ROLE_ID
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue, \
    get_permissions_structure, serialize_db_permissions
from gui.logic.db_helpers import beautify_db_entry
from gui.logic.filter_utils import filter_archived
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in
# pylint: disable=no-member,no-else-return

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('roles')
class Roles:

    @gui_route_logged_in(methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.GetUsersAndRoles, PermissionCategory.Settings))
    def get_roles(self):
        roles = [beautify_db_entry(entry) for entry in self._roles_collection.find(filter_archived({
            IS_AXONIUS_ROLE: {'$ne': True}
        }))]
        if not self.should_cloud_compliance_run():
            for role in roles:
                if role.get('permissions').get(PermissionCategory.Compliance.value):
                    del role.get('permissions')[PermissionCategory.Compliance.value]
        return jsonify(roles)

    @gui_route_logged_in('assignable_roles', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.GetUsersAndRoles, PermissionCategory.Settings))
    def get_assignable_roles(self):
        """
        Designated endpoint for getting only assignable roles list
        :return: set of roles (id and name only)
        """
        return jsonify(
            [{'text': entry.get('name'), 'value': str(entry.get('_id'))} for entry in self._roles_collection.find(
                filter_archived({
                    IS_AXONIUS_ROLE: {'$ne': True}
                }),
                projection={'name': 1}
            )])

    @gui_route_logged_in('<role_id>/assignees', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.Update, PermissionCategory.Settings, PermissionCategory.Roles))
    def get_role_assignees(self, role_id):
        match_users = {
            ROLE_ID: ObjectId(role_id)
        }
        existing_users = self._users_collection.find(filter_archived(match_users))
        return str(existing_users.count())

    @gui_route_logged_in(methods=['PUT'])
    def add_role(self):
        """
        Service for creating new roles.

        :return:
        """
        role_data = self.get_request_data_as_object()
        if 'name' not in role_data:
            logger.error('Name is required for saving a new role')
            return return_error('Name is required for saving a new role', 400)

        match_role = {
            'name': role_data['name']
        }

        existing_role = self._roles_collection.find_one(filter_archived(match_role))
        if existing_role:
            logger.error(f'Role by the name {role_data["name"]} already exists')
            return return_error(f'Role by the name {role_data["name"]} already exists', 400)
        self.fill_all_permission_actions(role_data.get('permissions'),
                                         serialize_db_permissions(get_permissions_structure(False)))

        result = self._roles_collection.replace_one(match_role, role_data, upsert=True)
        new_role_match = {
            '_id': ObjectId(result.upserted_id)
        }
        if not result.upserted_id:
            new_role_match = match_role
        new_role = self._roles_collection.find_one(filter_archived(new_role_match))

        return jsonify(beautify_db_entry(new_role))

    @staticmethod
    def fill_all_permission_actions(role_permissions, default_permission_structure):
        for category_name in default_permission_structure:
            default_category = default_permission_structure[category_name]
            role_category = role_permissions.get(category_name)
            if not role_category:
                role_permissions[category_name] = default_category
            elif PermissionCategory.has_value(category_name):
                Roles.fill_all_permission_actions(role_category, default_category)

    @gui_route_logged_in('<role_id>', methods=['POST'])
    def update_role(self, role_id):
        role_data = self.get_request_data_as_object()
        if 'name' not in role_data:
            logger.error('Name is required for saving a role')
            return return_error('Name is required for saving a role', 400)

        match_different_role_with_same_name = {
            '_id': {
                '$ne': ObjectId(role_id)
            },
            'name': role_data['name']
        }
        existing_role_with_same_name = self._roles_collection.find_one(filter_archived(
            match_different_role_with_same_name))
        if existing_role_with_same_name:
            logger.error(f'Another role by the name {role_data["name"]} was found')
            return return_error(f'Another role by the name {role_data["name"]} was found', 400)

        match_role = {
            '_id': ObjectId(role_id)
        }

        existing_role = self._roles_collection.find_one(filter_archived(match_role))
        if not existing_role:
            logger.error(f'Role {role_data["name"]} was not found')
            return return_error(f'Role {role_data["name"]} was not found', 400)
        if existing_role.get(PREDEFINED_FIELD):
            logger.error(f'Cannot edit {role_data["name"]} role')
            return return_error(f'Cannot edit {role_data["name"]} role', 400)
        self.fill_all_permission_actions(role_data.get('permissions'),
                                         serialize_db_permissions(get_permissions_structure(False)))
        self._roles_collection.replace_one({'_id': ObjectId(role_id)}, role_data, upsert=True)
        self._invalidate_sessions_for_role(role_id)
        role_data['_id'] = ObjectId(role_id)
        del role_data['uuid']
        return jsonify(beautify_db_entry(role_data))

    @gui_route_logged_in('<role_id>', methods=['DELETE'])
    def delete_roles(self, role_id):
        match_role = {
            '_id': ObjectId(role_id)
        }
        existing_role = self._roles_collection.find_one(filter_archived(match_role))
        if not existing_role:
            logger.error(f'Role by the id {role_id} and name {existing_role["name"]} was not found')
            return return_error(f'Role by the id {role_id} and name {existing_role["name"]} was not found', 400)

        if existing_role.get(PREDEFINED_FIELD):
            logger.error(f'Cannot delete {existing_role["name"]} role')
            return return_error(f'Cannot delete {existing_role["name"]} role', 400)

        match_users = {
            'role_id': ObjectId(role_id)
        }
        existing_users = self._users_collection.find(filter_archived(match_users))
        if existing_users.count() > 0:
            return return_error(f'Users are linked to this role and can\'t be deleted.\n'
                                f'Remove the linked users and try again', 403)

        self._roles_collection.update_one(match_role, {
            '$set': {
                'archived': True
            }
        })
        return json.dumps({
            'name': existing_role.get('name', '')
        })
