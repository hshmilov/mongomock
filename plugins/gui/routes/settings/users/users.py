import logging
import re
import secrets
from datetime import datetime

import pymongo
from bson import ObjectId
from flask import jsonify
from passlib.hash import bcrypt

from axonius.consts.gui_consts import (IS_AXONIUS_ROLE,
                                       PREDEFINED_ROLE_RESTRICTED,
                                       UNCHANGED_MAGIC_FOR_GUI, ROLE_ID, IGNORE_ROLE_ASSIGNMENT_RULES, PREDEFINED_FIELD)
from axonius.consts.plugin_consts import (ADMIN_USER_NAME,
                                          PASSWORD_LENGTH_SETTING,
                                          PASSWORD_MIN_LOWERCASE,
                                          PASSWORD_MIN_NUMBERS,
                                          PASSWORD_MIN_SPECIAL_CHARS,
                                          PASSWORD_MIN_UPPERCASE,
                                          PASSWORD_NO_MEET_REQUIREMENTS_MSG)
from axonius.logging.audit_helper import AuditAction, AuditType, AuditCategory
from axonius.plugin_base import return_error
from axonius.utils.gui_helpers import paginated, sorted_endpoint
from axonius.utils.permissions_helper import (PermissionAction,
                                              PermissionCategory,
                                              PermissionValue, get_restricted_permissions)
from gui.logic.db_helpers import translate_user_id_to_details
from gui.logic.filter_utils import filter_archived
from gui.logic.routing_helper import gui_route_logged_in, gui_section_add_rules
from gui.logic.users_helper import beautify_user_entry
from gui.routes.settings.users.tokens.user_token import USER_NAME

# pylint: disable=no-member,too-many-arguments

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('users')
class Users:

    @paginated()
    @sorted_endpoint()
    @gui_route_logged_in(methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.GetUsersAndRoles, PermissionCategory.Settings))
    def get_users(self, limit, skip, mongo_sort):
        """
        GET Returns all users of the system

        :param limit: limit for pagination
        :param skip: start index for pagination
        :param mongo_sort: sort the users by a field and a sort order
        :return:
        """
        return self._get_user_pages(limit=limit, skip=skip, sort=mongo_sort)

    @gui_route_logged_in('count', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.GetUsersAndRoles, PermissionCategory.Settings))
    def system_users_count(self):
        """
        :return: filtered users collection size (without axonius users)
        """
        role_ids_to_display = self._get_system_users_role_ids()
        users_collection = self._users_collection
        return jsonify(users_collection.count_documents(filter_archived({
            ROLE_ID: {
                '$in': role_ids_to_display
            }
        })))

    @gui_route_logged_in('username_list', methods=['GET'], required_permission=PermissionValue.get(
        PermissionAction.GetUsersAndRoles, PermissionCategory.Settings))
    def get_username_list(self):
        """
        Designated endpoint for getting all used user names
        :return: set of user names
        """
        users = self._users_collection.find(
            filter_archived({'source': 'internal'}),
            {'_id': False, USER_NAME: 1}
        )
        return jsonify([user.get(USER_NAME, '') for user in users])

    @gui_route_logged_in(methods=['PUT'], activity_params=[USER_NAME])
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
        if not post_data.get('auto_generated_password') and not self._check_password_validity(post_data['password']):
            return return_error(PASSWORD_NO_MEET_REQUIREMENTS_MSG, 403)

        password = post_data.get('password')
        if post_data.get('auto_generated_password'):
            password = secrets.token_urlsafe()
        user_name = post_data.get(USER_NAME)
        role_id = post_data.get(ROLE_ID)

        # Make sure all required fields provided
        if (not password) or (not role_id) or (not user_name):
            return 'Invalid request. Missing required fields', 400

        # Make sure user is unique by combo of name and source (no two users can have same name and same source)
        user_filter = filter_archived({
            USER_NAME: post_data[USER_NAME],
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

    def _create_restricted_role(self):
        insert_result = self._roles_collection.insert_one({
            'name': PREDEFINED_ROLE_RESTRICTED, PREDEFINED_FIELD: True,
            'permissions': get_restricted_permissions()
        })
        return insert_result.inserted_id

    def _create_user_if_doesnt_exist(self, username, first_name, last_name, email, picname=None, source='internal',
                                     password=None, role_id=None, assignment_rule_match_found=False,
                                     change_role_on_every_login=False):
        """
         Create a new user in the system if it does not exist already
        jim - 3.0 - made private instead of protected so api.py can use


        :param username: the username
        :param first_name: the first name
        :param last_name: the last name
        :param email: the email if there is one
        :param picname: the pic name url
        :param source: the source of the user - internal/<identity provider>
        :param password: the password, if empty it will generate a random password
        :param role_id: the user role id
        :param assignment_rule_match_found: if the role id is from an assignment rule
        :param change_role_on_every_login: if the role of this user should be changed
        if it was matched with a new role_id by the assignment rules
        :return: Created user/ Or the existing one
        """
        if source != 'internal' and password:
            password = bcrypt.hash(password)

        match_user = {
            USER_NAME: username,
            'source': source
        }
        user = self._users_collection.find_one(filter_archived(match_user))
        if not user:
            user = {
                USER_NAME: username,
                'first_name': first_name,
                'last_name': last_name,
                'pic_name': picname or self.DEFAULT_AVATAR_PIC,
                'source': source,
                'password': password,
                'api_key': secrets.token_urlsafe(),
                'api_secret': secrets.token_urlsafe(),
                'email': email,
                'last_updated': datetime.now(),
                'password_last_updated': datetime.utcnow(),
                IGNORE_ROLE_ASSIGNMENT_RULES: False,
            }
            if role_id:
                # Take the permissions set from the defined role
                role_doc = self._roles_collection.find_one(filter_archived({
                    '_id': ObjectId(role_id)
                }))
                if not role_doc or 'permissions' not in role_doc:
                    logger.error(f'The role id {role_id} was not found and default permissions will be used.')
                else:
                    user[ROLE_ID] = ObjectId(role_id)
            if ROLE_ID not in user:
                role_doc = self._roles_collection.find_one(filter_archived({
                    'name': PREDEFINED_ROLE_RESTRICTED
                }))
                user[ROLE_ID] = role_doc.get('_id') if role_doc else self._create_restricted_role()
            try:
                self._users_collection.replace_one(match_user, user, upsert=True)
                if source != 'internal':
                    self.log_activity_default('settings.users',
                                              'add_external_user',
                                              {USER_NAME: username, 'source': source.upper()},
                                              AuditType.Info)
            except pymongo.errors.DuplicateKeyError:
                logger.warning(f'Duplicate key error on {username}:{source}', exc_info=True)
            user = self._users_collection.find_one(filter_archived(match_user))
        elif role_id and role_id != user.get(ROLE_ID)\
                and not user.get(IGNORE_ROLE_ASSIGNMENT_RULES)\
                and change_role_on_every_login\
                and assignment_rule_match_found:
            user[ROLE_ID] = ObjectId(role_id)
            self._users_collection.update_one(match_user, {'$set': {ROLE_ID: user[ROLE_ID]}})
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
                               ROLE_ID: {
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

    @gui_route_logged_in('<user_id>', methods=['POST'], activity_params=[USER_NAME])
    def update_user(self, user_id):
        """
            Updates user info
        """
        return self._update_user(user_id)

    def _update_user(self, user_id):
        user = self._users_collection.find_one({'_id': ObjectId(user_id)})
        source = user.get('source')

        post_data = self.get_request_data_as_object()
        role_id = post_data.get(ROLE_ID)

        # axonius roles are not assignable
        axonius_roles_ids = self._get_axonius_roles_ids()
        if role_id in axonius_roles_ids:
            logger.info('Attempt to assign axonius role to users')
            return return_error('role is not assignable', 400)

        # Only admin users can update the 'admin' user
        if not self.is_admin_user() and user.get(USER_NAME) == ADMIN_USER_NAME:
            return return_error(f'Not allowed to update {user[USER_NAME]} user', 401)

        new_user_info = {
            ROLE_ID: ObjectId(role_id),
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
                new_user_info['password_last_updated'] = datetime.utcnow()
            elif password != UNCHANGED_MAGIC_FOR_GUI:
                return return_error(PASSWORD_NO_MEET_REQUIREMENTS_MSG, 403)
        else:
            new_user_info['ignore_role_assignment_rules'] = post_data.get('ignore_role_assignment_rules')
        logger.info(f'_update_user -> user_info {new_user_info}')
        updated_user = self._users_collection.find_one_and_update({
            '_id': ObjectId(user_id)
        }, {
            '$set': new_user_info
        }, return_document=pymongo.ReturnDocument.AFTER)
        if not updated_user:
            return '', 400
        translate_user_id_to_details.clean_cache()

        self._audit_assign_user_role(user_name=user.get(USER_NAME, ''),
                                     current_role_id=user.get(ROLE_ID),
                                     update_role_id=updated_user.get(ROLE_ID))

        self._invalidate_sessions([user_id])
        return jsonify({'user': beautify_user_entry(updated_user), 'uuid': user_id}), 200

    @gui_route_logged_in('<user_id>', methods=['DELETE'], activity_params=[USER_NAME])
    def delete_user(self, user_id):
        """
            Deleting a user
        """
        user = self._users_collection.find_one_and_update({'_id': ObjectId(user_id)},
                                                          {'$set': {'archived': True}},
                                                          {USER_NAME: 1})
        self._invalidate_sessions([user_id])

        translate_user_id_to_details.clean_cache()
        return jsonify({USER_NAME: user.get(USER_NAME, '')})

    def _audit_assign_user_role(self, user_name: str, current_role_id: ObjectId, update_role_id: ObjectId):
        if current_role_id != update_role_id:
            role = self._roles_collection.find_one({'_id': update_role_id})
            if role:
                self.log_activity_user(AuditCategory.UserManagement,
                                       AuditAction.AssignedRole,
                                       {USER_NAME: user_name, 'role': role.get('name', '')})
            else:
                logger.error(f'Skipping audit of missing Role Assigned {update_role_id} to user {user_name}')
