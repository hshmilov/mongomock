import logging
import secrets
import re

from datetime import datetime
import pymongo
from bson import ObjectId
from flask import (jsonify)
from passlib.hash import bcrypt

from axonius.consts.gui_consts import (PREDEFINED_ROLE_RESTRICTED, UNCHANGED_MAGIC_FOR_GUI,
                                       USERS_PREFERENCES_COLUMNS_FIELD, IS_AXONIUS_ROLE)

from axonius.consts.plugin_consts import PASSWORD_LENGTH_SETTING, PASSWORD_MIN_LOWERCASE, PASSWORD_MIN_UPPERCASE, \
    PASSWORD_MIN_NUMBERS, PASSWORD_MIN_SPECIAL_CHARS, PASSWORD_NO_MEET_REQUIREMENTS_MSG, PREDEFINED_USER_NAMES
from axonius.plugin_base import (return_error, EntityType,
                                 LIMITER_SCOPE, route_limiter_key_func)
from axonius.utils.gui_helpers import (paginated, sorted_endpoint)
from axonius.utils.permissions_helper import PermissionCategory, PermissionAction, PermissionValue

from gui.logic.db_helpers import translate_user_id_to_details
from gui.logic.filter_utils import filter_archived
from gui.logic.routing_helper import gui_section_add_rules, gui_route_logged_in
from gui.logic.users_helper import beautify_user_entry

# pylint: disable=no-member

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('users')
class Users:

    @paginated()
    @sorted_endpoint()
    @gui_route_logged_in(methods=['GET'],
                         required_permission_values={PermissionValue.get(PermissionAction.GetUsersAndRoles,
                                                                         PermissionCategory.Settings)})
    def get_users(self, limit, skip, mongo_sort):
        """
        GET Returns all users of the system

        :param limit: limit for pagination
        :param skip: start index for pagination
        :param mongo_sort: sort the users by a field and a sort order
        :return:
        """
        return self._get_user_pages(limit=limit, skip=skip, sort=mongo_sort)

    @gui_route_logged_in('count', methods=['GET'],
                         required_permission_values={PermissionValue.get(PermissionAction.GetUsersAndRoles,
                                                                         PermissionCategory.Settings)})
    def system_users_count(self):
        """
        :return: filtered users collection size (without axonius users)
        """
        role_ids_to_display = self._get_system_users_role_ids()
        users_collection = self._users_collection
        return jsonify(users_collection.count_documents(filter_archived({
            'role_id': {
                '$in': role_ids_to_display
            }
        })))

    @gui_route_logged_in('username_list', methods=['GET'],
                         required_permission_values={PermissionValue.get(PermissionAction.GetUsersAndRoles,
                                                                         PermissionCategory.Settings)})
    def get_username_list(self):
        """
        Designated endpoint for getting all used user names
        :return: set of user names
        """
        users = self._users_collection.find(
            filter_archived({'source': 'internal'}),
            {'_id': False, 'user_name': 1}
        )
        return jsonify([user.get('user_name', '') for user in users])

    @gui_route_logged_in(methods=['PUT'])
    def add_users(self):
        """
        PUT Create a new user

        :return:
        """
        return self._add_user_wrap()

    def _add_user_wrap(self):
        """Add a new user.

        Returns empty str.

        :return: str
        """
        post_data = self.get_request_data_as_object()
        if not self._check_password_validity(post_data['password']):
            return return_error(PASSWORD_NO_MEET_REQUIREMENTS_MSG, 403)

        password = post_data.get('password')
        user_name = post_data.get('user_name')
        role_id = post_data.get('role_id')

        # Make sure all required fields provided
        if (not password) or (not role_id) or (not user_name):
            return 'Invalid request. Missing required fields', 400

        # Make sure user is unique by combo of name and source (no two users can have same name and same source)
        user_filter = filter_archived({
            'user_name': post_data['user_name'],
            'source': 'internal'
        })

        if self._users_collection.find_one(user_filter):
            return return_error('User already exists', 400)

        password = bcrypt.hash(password)

        user = self._create_user_if_doesnt_exist(
            username=user_name,
            first_name=post_data.get('first_name'),
            last_name=post_data.get('last_name'),
            email=post_data.get('email'),
            picname=None,
            source='internal',
            password=password,
            role_id=ObjectId(role_id)
        )
        return jsonify(beautify_user_entry(user))

    def _create_user_if_doesnt_exist(self, username, first_name, last_name, email, picname=None, source='internal',
                                     password=None, role_id=None):
        """
        Create a new user in the system if it does not exist already
        jim - 3.0 - made private instead of protected so api.py can use

        :return: Created user
        """
        if source != 'internal' and password:
            password = bcrypt.hash(password)

        match_user = {
            'user_name': username,
            'source': source
        }
        user = self._users_collection.find_one(filter_archived(match_user))
        if not user:
            user = {
                'user_name': username,
                'first_name': first_name,
                'last_name': last_name,
                'pic_name': picname or self.DEFAULT_AVATAR_PIC,
                'source': source,
                'password': password,
                'api_key': secrets.token_urlsafe(),
                'api_secret': secrets.token_urlsafe(),
                'email': email,
                'last_updated': datetime.now()
            }
            if role_id:
                # Take the permissions set from the defined role
                role_doc = self._roles_collection.find_one(filter_archived({
                    '_id': ObjectId(role_id)
                }))
                if not role_doc or 'permissions' not in role_doc:
                    logger.error(f'The role id {role_id} was not found and default permissions will be used.')
                else:
                    user['role_id'] = ObjectId(role_id)
            if 'role_id' not in user:
                role_doc = self._roles_collection.find_one(filter_archived({
                    'name': PREDEFINED_ROLE_RESTRICTED
                }))
                user['role_id'] = role_doc.get('_id')
            try:
                self._users_collection.replace_one(match_user, user, upsert=True)
            except pymongo.errors.DuplicateKeyError:
                logger.warning(f'Duplicate key error on {username}:{source}', exc_info=True)
            user = self._users_collection.find_one(filter_archived(match_user))
        return user

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

    def _get_system_users_role_ids(self):
        return [entry.get('_id') for entry in self._roles_collection.find(filter_archived({
            IS_AXONIUS_ROLE: {'$ne': True}
        }))]

    def _get_user_pages(self, limit, skip, sort=None):
        find_sort = [('_id', pymongo.ASCENDING)]
        if sort:
            find_sort = list(sort.items())
        role_ids_to_display = self._get_system_users_role_ids()
        return jsonify(beautify_user_entry(n) for n in
                       self._users_collection.find(filter_archived(
                           {
                               'role_id': {
                                   '$in': role_ids_to_display
                               }
                           })).sort(find_sort)
                       .skip(skip)
                       .limit(limit))

    def _get_axonius_roles_ids(self):
        axonius_roles = self._roles_collection.find({
            IS_AXONIUS_ROLE: True
        })
        return [role.get('_id', '') for role in axonius_roles]

    @gui_route_logged_in('assign_role', methods=['POST'])
    def users_assign_role_bulk(self):
        """
        set new role_id to all users or all users with id found in a given set.
        :return:
        status code 200 - updated all requested users
        status code 202 - the request partially succeed. Not akk users archived
        status code 400 - invalid request. role_id not supplied
        status code 500 - server error. Operation failed.
        """
        users_collection = self._users_collection
        request_data = self.get_request_data_as_object()
        ids = request_data.get('ids', [])
        include = request_data.get('include', True)
        role_id = request_data.get('role_id')

        # axonius roles is not assignable
        axonius_roles_ids = self._get_axonius_roles_ids()
        if role_id in axonius_roles_ids:
            logger.info('Attempt to assign axonius role to users')
            return return_error('role is not assignable', 400)

        if not role_id:
            return return_error('role id is required', 400)

        # if include value is False, all users should be updated (beside admin, _axonius and _axonius_ro)
        find_query = {}
        if not include:
            find_query = filter_archived({
                '_id': {'$nin': [ObjectId(user_id) for user_id in ids]},
                'user_name': {'$nin': PREDEFINED_USER_NAMES},
            })
        else:
            find_query = filter_archived({
                '_id': {'$in': [ObjectId(user_id) for user_id in ids]},
                'user_name': {'$nin': PREDEFINED_USER_NAMES},
            })

        result = users_collection.update_many(find_query, {
            '$set': {'role_id': ObjectId(role_id), 'last_updated': datetime.now()}
        })

        if result.modified_count < 1:
            logger.info('operation failed, could not update users\' role')
            return return_error('operation failed, could not update users\' role', 500)
        user_ids = [str(user_id.get('_id')) for user_id in users_collection.find(find_query, {'_id': 1})]
        self._invalidate_sessions(user_ids)
        if result.matched_count != result.modified_count:
            logger.info(f'Bulk assign role modified {result.modified_count} out of {result.matched_count}')
            return '', 202

        logger.info(f'Bulk assign role modified succeeded')
        return '', 200

    @gui_route_logged_in('<user_id>', methods=['POST'])
    def update_user(self, user_id):
        """
            Updates user info
        """
        return self._update_user(user_id)

    def _update_user(self, user_id):
        user = self._users_collection.find_one({'_id': ObjectId(user_id)})
        source = user.get('source')

        post_data = self.get_request_data_as_object()
        role_id = post_data.get('role_id')

        # axonius roles are not assignable
        axonius_roles_ids = self._get_axonius_roles_ids()
        if role_id in axonius_roles_ids:
            logger.info('Attempt to assign axonius role to users')
            return return_error('role is not assignable', 400)

        new_user_info = {
            'role_id': ObjectId(role_id),
            'last_updated': datetime.now()
        }

        if source == 'internal':
            # For internal users, more fields can be updated beside the role_id
            new_user_info['first_name'] = post_data.get('first_name')
            new_user_info['last_name'] = post_data.get('last_name')
            new_user_info['email'] = post_data.get('email')

            password = post_data.get('password')
            if password != UNCHANGED_MAGIC_FOR_GUI and self._check_password_validity(password):
                new_user_info['password'] = bcrypt.hash(password)
            elif password != UNCHANGED_MAGIC_FOR_GUI:
                return return_error(PASSWORD_NO_MEET_REQUIREMENTS_MSG, 403)
        logger.info(f'_update_user -> user_info {new_user_info}')
        updated_user = self._users_collection.find_one_and_update({
            '_id': ObjectId(user_id)
        }, {
            '$set': new_user_info
        }, return_document=pymongo.ReturnDocument.AFTER)
        if not updated_user:
            return '', 400
        translate_user_id_to_details.clean_cache()
        self._invalidate_sessions([user_id])
        return jsonify({'user': beautify_user_entry(updated_user), 'uuid': user_id}), 200

    @gui_route_logged_in('<user_id>', methods=['DELETE'])
    def delete_user(self, user_id):
        """
            Deleting a user
        """
        self._users_collection.update_one({'_id': ObjectId(user_id)},
                                          {'$set': {'archived': True}})
        self._invalidate_sessions([user_id])

        translate_user_id_to_details.clean_cache()
        return '', 200

    @gui_route_logged_in(methods=['DELETE'])
    def delete_users_bulk(self):
        """
        archive all users or all users with id found in a given set.
        :return:
        status code 200 - archived all requested users and invalidate their session
        status code 202 - the request partially succeed. Not akk users archived
        status code 500 - server error. Operation failed.
        """
        users_collection = self._users_collection
        request_data = self.get_request_data_as_object()
        ids = request_data.get('ids', [])
        include = request_data.get('include', True)

        # if include is equal to False, all users should be deleted beside admin, _axonius & _axonius_ro
        if not include:
            logger.info('Update users with include = False')
            result = users_collection.update_many(filter_archived({
                'user_name': {'$nin': PREDEFINED_USER_NAMES},
                '_id': {'$nin': [ObjectId(user_id) for user_id in ids]}
            }), {
                '$set': {'archived': True}
            })

            # handle response
            if result.modified_count < 1:
                err_msg = 'operation failed, could not delete users\''
                logger.info(err_msg)
                return return_error(err_msg, 500)

            if result.matched_count != result.modified_count:
                logger.info(f'Deleted {result.modified_count} out of {result.matched_count} users')
                return '', 202

            logger.info(f'Bulk deletion users succeeded')
            return '', 200

        partial_success = False
        deletion_success = False
        for user_id in ids:
            existed_user = users_collection.find_one_and_update(filter_archived({
                '_id': ObjectId(user_id)
            }), {
                '$set': {'archived': True}
            }, projection={
                'user_name': 1
            })

            if existed_user is None:
                logger.info(f'User with id {user_id} does not exists')
                partial_success = True
            deletion_success = True
            self._invalidate_sessions([user_id])
            name = existed_user['user_name']
            logger.info(f'Users {name} with id {user_id} has been archive')

        # handle response
        if not deletion_success:
            err_msg = 'operation failed, could not delete users\''
            logger.info(err_msg)
            return return_error(err_msg, 500)
        if deletion_success and partial_success:
            logger.info('Deletion partially succeeded')
            return '', 202
        logger.info(f'Bulk deletion users succeeded')
        return '', 200

    @gui_route_logged_in('self/password', methods=['POST'], enforce_permissions=False,
                         limiter_key_func=route_limiter_key_func, shared_limit_scope=LIMITER_SCOPE)
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
        self._invalidate_sessions([str(user['_id'])])
        return '', 200

    @gui_route_logged_in('self/preferences', methods=['GET'], enforce_permissions=False)
    def get_system_users_preferences(self):
        """
        Fetch the default view of devices table, for current user
        """
        return self._system_users_preferences_get()

    @gui_route_logged_in('self/preferences', methods=['POST'], enforce_permissions=False)
    def update_system_users_preferences(self):
        """
        Save the default view of devices table, for current user
        """
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
