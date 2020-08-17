import logging
import secrets
from datetime import datetime

from bson import ObjectId
from flask import jsonify
from passlib.hash import bcrypt

from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.gui_consts import (USERS_TOKENS_EMAIL_INVITE_SUBJECT,
                                       USERS_TOKENS_EMAIL_SUBJECT,
                                       USERS_TOKENS_INVITE_EMAIL_CONTENT,
                                       USERS_TOKENS_RESET_EMAIL_CONTENT,
                                       USERS_TOKENS_RESET_LINK, USER_NAME)
from axonius.consts.plugin_consts import (ADMIN_USER_NAME,
                                          PASSWORD_NO_MEET_REQUIREMENTS_MSG,
                                          RESET_PASSWORD_LINK_EXPIRATION,
                                          RESET_PASSWORD_SETTINGS)
from axonius.logging.audit_helper import AuditAction, AuditCategory, AuditType
from axonius.plugin_base import return_error
from axonius.utils.permissions_helper import PermissionCategory
from gui.logic.routing_helper import gui_route_logged_in, gui_section_add_rules

# pylint: disable=no-member

logger = logging.getLogger(f'axonius.{__name__}')


@gui_section_add_rules('users/tokens', permission_section=PermissionCategory.Users)
class UserToken:

    @gui_route_logged_in('generate', methods=['PUT', 'POST'], activity_params=[USER_NAME])
    def generate_user_reset_password_link(self, manual_user_id: str = ''):
        """
        Gets user ID and generate reset password token
        user id expected to be plain text, not ObjectId
        :return: link to current machine reset password page, with the token as url param
        """
        if not manual_user_id:
            post_data = self.get_request_data_as_object()
            user_id = post_data.get('user_id')
        else:
            user_id = manual_user_id
        if not user_id:
            return return_error('please provide valid user id', 400)

        user = self._users_collection.find_one({
            '_id': ObjectId(user_id)
        })
        if not user:
            return return_error('please provide valid user id', 400)

        # Only admin users can create a reset link for the 'admin' user
        if not manual_user_id and not self.is_admin_user() and user.get('user_name') != ADMIN_USER_NAME:
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

    @gui_route_logged_in('validate/<token>', methods=['GET'], enforce_session=False)
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

    @gui_route_logged_in('reset',
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

        user = self._users_collection.find_one({
            '_id': ObjectId(user_id)
        }, projection={'password': 1})

        if bcrypt.verify(post_data['password'], user['password']):
            return return_error('Your new password must be different from your previous password.', 400)

        user = self._users_collection.find_one_and_update({
            '_id': ObjectId(user_id)
        }, {
            '$set': {
                'password': bcrypt.hash(post_data['password']),
                'password_last_updated': datetime.utcnow()
            }
        }, {USER_NAME: 1, 'password': 1})

        if not user:
            return return_error(f'error updating password for user id {user_id}', 400)

        self._users_tokens_collection.delete_one(match_token)
        self._invalidate_sessions([user_id])

        user_name = f'\'{user.get(USER_NAME)}\'' if user.get(USER_NAME) else ''
        self.log_activity_default(AuditCategory.UserSession.value,
                                  AuditAction.ChangedPassword.value,
                                  {USER_NAME: user_name},
                                  AuditType.Info)

        return jsonify({USER_NAME: user.get(USER_NAME, '')})

    @gui_route_logged_in('notify', methods=['PUT', 'POST'], activity_params=[USER_NAME])
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
        if not user_token:
            return return_error('token error', 400)

        user = self._users_collection.find_one({'_id': user_id})
        system_config = self.system_collection.find_one({'type': 'server'}) or {}
        server_name = system_config.get('server_name', 'localhost')
        reset_link = USERS_TOKENS_RESET_LINK.format(server_name=server_name,
                                                    token=user_token['token'])
        try:
            self._send_reset_password_email(reset_link, email_address, invite, user[USER_NAME])
        except RuntimeWarning as e:
            return return_error(str(e), 412)
        except Exception as e:
            return return_error(str(e), 500)
        return jsonify({USER_NAME: user.get(USER_NAME, '')})

    def _send_reset_password_email(self, link, email_address, invite: bool = False, user_name: str = None):
        core_config = self.plugins.core.configurable_configs[CORE_CONFIG_NAME]
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
