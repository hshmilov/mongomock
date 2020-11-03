# pylint: disable=no-member

import logging
from datetime import datetime

from bson import ObjectId
from flask import jsonify

from axonius.consts.gui_consts import USERS_PREFERENCES_COLUMNS_FIELD
from axonius.consts.plugin_consts import PASSWORD_NO_MEET_REQUIREMENTS_MSG
from axonius.plugin_base import (EntityType, LIMITER_SCOPE, route_limiter_key_func, return_error)
from axonius.utils.gui_helpers import get_connected_user_id
from axonius.utils.hash import verify_user_password, user_password_handler
from gui.logic.db_helpers import clean_user_cache
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules('self')
class Account:

    @gui_route_logged_in('password', methods=['POST'], enforce_permissions=False,
                         limiter_key_func=route_limiter_key_func, shared_limit_scope=LIMITER_SCOPE)
    def system_users_password(self):
        """
        Change a password for a specific user. It must be the same user as currently logged in to the system.
        Post data is expected to have the old password, matching the one in the DB

        path: /api/self/password

        :param user_id:
        :return:
        """
        post_data = self.get_request_data_as_object()
        user = self.get_user
        if not user or not user.get('password'):
            return return_error('Not logged in', 401)
        encrypted_password = user['password']
        if isinstance(encrypted_password, list):
            encrypted_password = ''.join([chr(c) for c in encrypted_password])
        if not verify_user_password(post_data.get('old', ''), encrypted_password, user.get('salt')):
            return return_error('Given password is wrong', 400)

        if not self._check_password_validity(post_data['new']):
            return return_error(PASSWORD_NO_MEET_REQUIREMENTS_MSG, 403)

        password, salt = user_password_handler(post_data['new'])
        self._users_collection.update_one(
            {'_id': ObjectId(user['_id'])},
            {
                '$set': {
                    'password': password,
                    'salt': salt,
                    'password_last_updated': datetime.utcnow()
                }
            })
        clean_user_cache()
        return '', 200

    @gui_route_logged_in('preferences', methods=['GET'], enforce_permissions=False)
    def get_system_users_preferences(self):
        """
        Fetch the default view of devices table, for current user

        path: /api/self/preferences
        """
        return self._system_users_preferences_get()

    @gui_route_logged_in('preferences', methods=['POST'], enforce_permissions=False)
    def update_system_users_preferences(self):
        """
        Save the default view of devices table, for current user

        path: /api/self/preferences
        """
        post_data = self.get_request_data_as_object()
        self._users_preferences_collection.update_one({
            'user_id': get_connected_user_id()
        }, {
            '$set': self.prepare_column_preferences(post_data)
        }, upsert=True)
        return '', 200

    def _system_users_preferences_get(self):
        """
        Search for current user's preferences and it
        :return: List of saved fields or error if none found
        """

        user_preferences = self._users_preferences_collection.find_one({
            'user_id': get_connected_user_id()
        })
        if not user_preferences:
            return jsonify({}), 200
        return jsonify(user_preferences), 200

    @staticmethod
    def prepare_column_preferences(post_data):
        set_object = {}
        for entity_type in EntityType:
            entity_value = entity_type.value
            if entity_value in post_data:
                table_columns_preferences = post_data[entity_value].get(USERS_PREFERENCES_COLUMNS_FIELD, {})
                for (view_type, columns) in table_columns_preferences.items():
                    set_object[f'{entity_value}.{USERS_PREFERENCES_COLUMNS_FIELD}.{view_type}'] = columns
        return set_object
