import logging
import re

import pymongo
from bson import ObjectId
from flask import (jsonify,
                   request)
from passlib.hash import bcrypt

from axonius.consts.gui_consts import (PREDEFINED_ROLE_ADMIN,
                                       UNCHANGED_MAGIC_FOR_GUI,
                                       USERS_PREFERENCES_COLUMNS_FIELD)
from axonius.consts.plugin_consts import PASSWORD_LENGTH_SETTING, PASSWORD_MIN_LOWERCASE, PASSWORD_MIN_UPPERCASE, \
    PASSWORD_MIN_NUMBERS, PASSWORD_MIN_SPECIAL_CHARS, PASSWORD_NO_MEET_REQUIREMENTS_MSG
from axonius.plugin_base import (return_error, EntityType)
from axonius.utils.gui_helpers import (Permission, PermissionLevel,
                                       PermissionType, get_connected_user_id,
                                       is_admin_user, paginated)
from gui.logic.db_helpers import translate_user_id_to_details
from gui.logic.filter_utils import filter_archived
from gui.logic.routing_helper import gui_add_rule_logged_in
from gui.logic.users_helper import beautify_user_entry
# pylint: disable=no-member

logger = logging.getLogger(f'axonius.{__name__}')


class Users:

    @paginated()
    @gui_add_rule_logged_in('system/users', methods=['GET', 'PUT'],
                            required_permissions={Permission(PermissionType.Settings, PermissionLevel.ReadWrite)})
    def system_users(self, limit, skip):
        """
        GET Returns all users of the system
        PUT Create a new user

        :param limit: limit for pagination
        :param skip: start index for pagination
        :return:
        """
        if request.method == 'GET':
            return self._get_user_pages(limit=limit, skip=skip)
        # Handle PUT - only option left
        role_name = self.get_session.get('user', {}).get('role_name', '')
        is_admin = is_admin_user()
        return self._add_user_wrap(role_name=role_name, is_admin=is_admin)

    def _add_user_wrap(self, role_name, is_admin):
        """Add a new user.

        Returns empty str.

        :return: str
        """
        if role_name != PREDEFINED_ROLE_ADMIN and not is_admin:
            return return_error('Only admin users are permitted to create users!', 401)

        post_data = self.get_request_data_as_object()
        if not self._check_password_validity(post_data['password']):
            return return_error(PASSWORD_NO_MEET_REQUIREMENTS_MSG, 403)

        post_data['password'] = bcrypt.hash(post_data['password'])

        # Make sure user is unique by combo of name and source (no two users can have same name and same source)
        find_data = {
            'user_name': post_data['user_name'],
            'source': 'internal'
        }

        find_filter = filter_archived(find_data)

        if self._users_collection.find_one(find_filter):
            return return_error('User already exists', 400)

        self._create_user_if_doesnt_exist(
            post_data['user_name'],
            post_data['first_name'],
            post_data['last_name'],
            picname=None,
            source='internal',
            password=post_data['password'],
            role_name=post_data.get('role_name')
        )
        return ''

    # pylint: disable=too-many-return-statements
    def _check_password_validity(self, password):
        password_policy = self._password_policy_settings
        if not password_policy['enabled']:
            return True
        if len(password) < password_policy[PASSWORD_LENGTH_SETTING]:
            return False
        if len(re.findall('[a-z]', password)) < password_policy[PASSWORD_MIN_LOWERCASE]:
            return False
        if len(re.findall('[A-Z]', password)) < password_policy[PASSWORD_MIN_UPPERCASE]:
            return False
        if len(re.findall('[0-9]', password)) < password_policy[PASSWORD_MIN_NUMBERS]:
            return False
        if len(re.findall(r'[~!@#$%^&*_\-+=`\|\\\\()\{\}\[\]:;"\'<>,.?/]', password)) < \
                password_policy[PASSWORD_MIN_SPECIAL_CHARS]:
            return False
        return True

    def _get_user_pages(self, limit, skip):
        return jsonify(beautify_user_entry(n) for n in
                       self._users_collection.find(filter_archived(
                           {
                               'user_name': {
                                   '$ne': self.ALTERNATIVE_USER['user_name']
                               }
                           })).sort([('_id', pymongo.ASCENDING)])
                       .skip(skip)
                       .limit(limit))

    @gui_add_rule_logged_in('system/users/<user_id>', methods=['POST', 'DELETE'],
                            required_permissions={Permission(PermissionType.Settings, PermissionLevel.ReadWrite)})
    def update_user(self, user_id):
        """
            Updates the userinfo for the current user or deleting a user
        """
        return self._update_user(user_id)

    def _update_user(self, user_id):
        if request.method == 'POST':
            update_white_list_fields = ['first_name', 'last_name', 'password']
            post_data = self.get_request_data_as_object()
            user_data = {}
            for key, value in post_data.items():
                if key not in update_white_list_fields:
                    continue
                if key == 'password':
                    if value != UNCHANGED_MAGIC_FOR_GUI and self._check_password_validity(value):
                        user_data[key] = bcrypt.hash(value)
                    elif value != UNCHANGED_MAGIC_FOR_GUI:
                        return return_error(PASSWORD_NO_MEET_REQUIREMENTS_MSG, 403)
                else:
                    user_data[key] = value

            res = self._users_collection.update_one({
                '_id': ObjectId(user_id)
            }, {
                '$set': user_data
            })
            if not res.matched_count:
                return '', 400
        if request.method == 'DELETE':
            self._users_collection.update_one({'_id': ObjectId(user_id)},
                                              {'$set': {'archived': True}})
            self._invalidate_sessions(user_id)

        translate_user_id_to_details.clean_cache()
        return '', 200

    @gui_add_rule_logged_in('system/users/self/additional_userinfo', methods=['POST'])
    def system_users_additional_userinfo(self):
        """
        Updates the userinfo for the current user
        :return:
        """
        return self._system_users_additional_userinfo()

    def _system_users_additional_userinfo(self):
        post_data = self.get_request_data_as_object()

        self._users_collection.update_one({
            '_id': get_connected_user_id()
        }, {
            '$set': {
                'additional_userinfo': post_data
            }
        })
        return '', 200

    @gui_add_rule_logged_in('system/users/self/password', methods=['POST'])
    def system_users_password(self):
        """
        Change a password for a specific user. It must be the same user as currently logged in to the system.
        Post data is expected to have the old password, matching the one in the DB

        :param user_id:
        :return:
        """
        post_data = self.get_request_data_as_object()
        user = self.get_session['user']
        if not bcrypt.verify(post_data['old'], user['password']):
            return return_error('Given password is wrong')

        if not self._check_password_validity(post_data['new']):
            return return_error(PASSWORD_NO_MEET_REQUIREMENTS_MSG, 403)

        self._users_collection.update_one({'_id': user['_id']},
                                          {'$set': {'password': bcrypt.hash(post_data['new'])}})
        self._invalidate_sessions(user['_id'])
        return '', 200

    @gui_add_rule_logged_in('system/users/<user_id>/access', methods=['POST'],
                            required_permissions={Permission(PermissionType.Settings,
                                                             PermissionLevel.ReadWrite)})
    def system_users_access(self, user_id):
        """
        Change permissions for a specific user, given the correct permissions.
        Post data is expected to contain the permissions object and the role, if there is one.

        :param user_id:
        :return:
        """
        return self._system_users_access(user_id=user_id)

    def _system_users_access(self, user_id):
        """
        Change permissions for a specific user, given the correct permissions.
        Post data is expected to contain the permissions object and the role, if there is one.

        :param user_id:
        :return:
        """
        post_data = self.get_request_data_as_object()
        params = ['permissions', 'role_name']
        update_data = {param: post_data[param] for param in params}
        self._users_collection.update_one({'_id': ObjectId(user_id)},
                                          {'$set': update_data})
        self._invalidate_sessions(user_id)
        return ''

    @gui_add_rule_logged_in('system/users/self/preferences', methods=['GET', 'POST'])
    def system_users_preferences(self):
        """
        Fetch or save the default view of devices table, for current user
        """
        if request.method == 'GET':
            return self._system_users_preferences_get()
        # Handle POST alternatively
        return self._system_users_preferences_post()

    def _system_users_preferences_get(self):
        """
        Search for current user's preferences and it

        :return: List of saved fields or error if none found
        """
        user_preferences = self._users_preferences_collection.find_one({
            'user_id': self.get_session['user']['_id']
        })
        if not user_preferences:
            return jsonify({}), 200
        return jsonify(user_preferences), 200

    def _system_users_preferences_post(self):
        """
        Save a default view for given entity_type, in current user's preferences

        :param entity_type: devices | users
        :return: Error if could not save
        """
        post_data = self.get_request_data_as_object()
        set_object = {}
        for entity_type in EntityType:
            entity_value = entity_type.value
            if entity_value in post_data:
                table_columns_preferences = post_data[entity_value].get(USERS_PREFERENCES_COLUMNS_FIELD, {})
                for (view_type, columns) in table_columns_preferences.items():
                    set_object[f'{entity_value}.{USERS_PREFERENCES_COLUMNS_FIELD}.{view_type}'] = columns
        self._users_preferences_collection.update_one({
            'user_id': self.get_session['user']['_id']
        }, {
            '$set': set_object
        }, upsert=True)
        return '', 200
