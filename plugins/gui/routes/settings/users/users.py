import logging
import secrets
import re
import json

from datetime import datetime
import pymongo
from bson import ObjectId
from flask import (jsonify)
from passlib.hash import bcrypt

from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.gui_consts import (PREDEFINED_ROLE_RESTRICTED, UNCHANGED_MAGIC_FOR_GUI, IS_AXONIUS_ROLE,
                                       USERS_TOKENS_EMAIL_SUBJECT, USERS_TOKENS_RESET_EMAIL_CONTENT,
                                       USERS_TOKENS_RESET_LINK, USERS_TOKENS_INVITE_EMAIL_CONTENT,
                                       USERS_TOKENS_EMAIL_INVITE_SUBJECT)

from axonius.consts.plugin_consts import (PASSWORD_LENGTH_SETTING,
                                          PASSWORD_MIN_LOWERCASE, PASSWORD_MIN_UPPERCASE,
                                          PASSWORD_MIN_NUMBERS, PASSWORD_MIN_SPECIAL_CHARS,
                                          PASSWORD_NO_MEET_REQUIREMENTS_MSG, PREDEFINED_USER_NAMES,
                                          CORE_UNIQUE_NAME, CONFIGURABLE_CONFIGS_COLLECTION,
                                          RESET_PASSWORD_LINK_EXPIRATION, RESET_PASSWORD_SETTINGS, ADMIN_USER_NAME)
from axonius.plugin_base import return_error
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
            'role_id': {
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
            {'_id': False, 'user_name': 1}
        )
        return jsonify([user.get('user_name', '') for user in users])

    @gui_route_logged_in(methods=['PUT'], activity_params=['user_name'])
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

    @gui_route_logged_in('assign_role', methods=['POST'], activity_params=['name', 'count'])
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
        if ObjectId(role_id) in axonius_roles_ids:
            logger.info('Attempt to assign axonius role to users')
            return return_error('role is not assignable', 400)

        if not role_id:
            return return_error('role id is required', 400)

        # if include value is False, all users should be updated (beside admin, _axonius and _axonius_ro)
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
            return return_error('operation failed, could not update users\' role', 400)
        user_ids = [str(user_id.get('_id')) for user_id in users_collection.find(find_query, {'_id': 1})]
        self._invalidate_sessions(user_ids)
        response_str = json.dumps({
            'count': str(result.modified_count),
            'name': self._roles_collection.find_one({'_id': ObjectId(role_id)}, {'name': 1}).get('name', '')
        })
        if result.matched_count != result.modified_count:
            logger.info(f'Bulk assign role modified {result.modified_count} out of {result.matched_count}')
            return response_str, 202

        logger.info(f'Bulk assign role modified succeeded')
        return response_str, 200

    @gui_route_logged_in('<user_id>', methods=['POST'], activity_params=['user_name'])
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

        # Only admin users can update the 'admin' user
        if not self.is_admin_user() and user.get('user_name') == ADMIN_USER_NAME:
            return return_error(f'Not allowed to update {user["user_name"]} user', 401)

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

    @gui_route_logged_in(methods=['DELETE'], activity_params=['count'])
    def delete_users_bulk(self):
        """
        archive all users or all users with id found in a given set.
        :return:
        status code 200 - archived all requested users and invalidate their session
        status code 202 - the request partially succeed. Not akk users archived
        status code 400 - server error. Operation failed.
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
                return return_error(err_msg, 400)

            response_str = json.dumps({
                'count': str(result.modified_count)
            })
            if result.matched_count != result.modified_count:
                logger.info(f'Deleted {result.modified_count} out of {result.matched_count} users')
                return response_str, 202

            logger.info(f'Bulk deletion users succeeded')
            return response_str, 200

        partial_success = False
        deletion_success = False
        deletion_count = 0
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
            else:
                deletion_count += 1
            deletion_success = True
            self._invalidate_sessions([user_id])
            name = existed_user['user_name']
            logger.info(f'Users {name} with id {user_id} has been archive')

        # handle response
        if not deletion_success:
            err_msg = 'operation failed, could not delete users\''
            logger.info(err_msg)
            return return_error(err_msg, 400)
        response_str = json.dumps({
            'count': str(deletion_count)
        })
        if deletion_success and partial_success:
            logger.info('Deletion partially succeeded')
            return response_str, 202
        logger.info(f'Bulk deletion users succeeded')
        return response_str, 200

    @gui_route_logged_in('tokens/create/reset_password', methods=['PUT', 'POST'])
    def generate_user_reset_password_link(self):
        """
        Gets user ID and generate reset password token
        user id expected to be plain text, not ObjectId
        :return: link to current machine reset password page, with the token as url param
        """
        post_data = self.get_request_data_as_object()
        user_id = post_data.get('user_id')
        if not user_id:
            return return_error('please provide valid user id', 400)

        user = self._users_collection.find_one({
            '_id': ObjectId(user_id)
        })
        if not user:
            return return_error('please provide valid user id', 400)

        # Only admin users can create a reset link for the 'admin' user
        if not self.is_admin_user() and user.get('user_name') == ADMIN_USER_NAME:
            return return_error(f'Not allowed to reset {user["user_name"]} user', 401)

        token = secrets.token_urlsafe()
        result = self._users_tokens_collection.update_one({
            'user_id': ObjectId(user_id)
        }, {
            '$set': {
                'token': token,
                'date_added': datetime.utcnow(),
                'type': 'reset_password'
            }
        }, upsert=True)
        if not result:
            return return_error('token cannot created', 400)

        system_config = self.system_collection.find_one({'type': 'server'}) or {}
        server_name = system_config.get('server_name', 'localhost')

        return USERS_TOKENS_RESET_LINK.format(server_name=server_name, token=token)

    @gui_route_logged_in('tokens/validate/reset_password/<token>', methods=['GET'], enforce_session=False)
    def verify_user_reset_password_token(self, token):
        """
        Search for current user's reset password token
        if no token exist, its count as expired
        :param: token: a valid token for user reset password
        :return: boolean representation of token status, valid or expired in any other case
        """
        user_token = self._users_tokens_collection.find_one({
            'token': token,
            'type': 'reset_password'
        })
        return jsonify({'valid': bool(user_token)}), 200

    @gui_route_logged_in('tokens/reset_password',
                         methods=['POST'],
                         enforce_session=False,
                         enforce_permissions=False)
    def reset_user_password_by_token(self):
        """
        Change user password verified by the reset password token, new password expected to be in post_data
        :param token: a valid token for user reset password
        :return:
        """
        post_data = self.get_request_data_as_object()
        if not self._check_password_validity(post_data.get('password')):
            return return_error(PASSWORD_NO_MEET_REQUIREMENTS_MSG, 403)

        token = post_data.get('token')
        if not token:
            return return_error('token error', 400)

        match_token = {
            'token': token,
            'type': 'reset_password'
        }
        user_token = self._users_tokens_collection.find_one(match_token)
        if not user_token:
            return return_error('token error', 400)

        user_id = user_token.get('user_id')

        result = self._users_collection.update_one({
            '_id': ObjectId(user_id)
        }, {
            '$set': {
                'password': bcrypt.hash(post_data['password'])
            }
        })
        if not result.modified_count or not result.matched_count:
            return return_error(f'error updating password count:{result.modified_count} matched:{result.matched_count}',
                                400)
        self._users_tokens_collection.delete_one(match_token)
        self._invalidate_sessions([user_id])
        return '', 200

    @gui_route_logged_in('tokens/send_reset_password', methods=['PUT', 'POST'])
    def send_reset_password(self):
        post_data = self.get_request_data_as_object()
        if not post_data.get('user_id'):
            return return_error('please provide valid user id', 400)
        user_id = ObjectId(post_data['user_id'])
        email_address = post_data.get('email')
        if not email_address:
            return return_error('please provide valid email address', 400)

        invite = post_data.get('invite')
        user_token = self._users_tokens_collection.find_one({
            'user_id': user_id,
            'type': 'reset_password'
        })
        user = self._users_collection.find_one({'_id': user_id})
        system_config = self.system_collection.find_one({'type': 'server'}) or {}
        server_name = system_config.get('server_name', 'localhost')
        reset_link = USERS_TOKENS_RESET_LINK.format(server_name=server_name,
                                                    token=user_token['token'])
        try:
            self._send_reset_password_email(reset_link, email_address, invite, user['user_name'])
        except RuntimeWarning as e:
            return return_error(str(e), 412)
        except Exception as e:
            return return_error(str(e), 500)
        return '', 204

    def _send_reset_password_email(self, link, email_address, invite: bool = False, user_name: str = None):
        core_config = self._get_db_connection()[CORE_UNIQUE_NAME][CONFIGURABLE_CONFIGS_COLLECTION].find_one(
            {'config_name': CORE_CONFIG_NAME})['config']
        expire_hours = core_config.get(RESET_PASSWORD_SETTINGS).get(RESET_PASSWORD_LINK_EXPIRATION)
        if self.mail_sender:
            try:
                if not invite:
                    subject = USERS_TOKENS_EMAIL_SUBJECT
                    content = USERS_TOKENS_RESET_EMAIL_CONTENT.format(link=link,
                                                                      expire_hours=expire_hours)
                else:
                    subject = USERS_TOKENS_EMAIL_INVITE_SUBJECT
                    content = USERS_TOKENS_INVITE_EMAIL_CONTENT.format(link=link,
                                                                       expire_hours=expire_hours,
                                                                       user_name=user_name)
                email = self.mail_sender.new_email(subject,
                                                   [email_address])
                email.send(content.replace('\n', '\n<br>'))
                logger.info(f'The reset password link was sent to {email_address}')
            except Exception:
                error_message = f'Failed to send a reset password link to {email_address}'
                logger.info(error_message)
                raise Exception(error_message)
        else:
            logger.info('Email cannot be sent because no email server is configured')
            raise RuntimeWarning('No email server configured')
