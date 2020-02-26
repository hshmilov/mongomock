from datetime import datetime, timedelta

from flask import (jsonify,
                   request)
from passlib.hash import bcrypt

from axonius.consts import gui_consts
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.plugin_consts import (CONFIGURABLE_CONFIGS_COLLECTION,
                                          CORE_UNIQUE_NAME,
                                          GUI_PLUGIN_NAME)
from axonius.plugin_base import return_error
from axonius.utils.gui_helpers import add_rule_unauth
from gui.feature_flags import FeatureFlags
from gui.logic.login_helper import has_customer_login_happened
# pylint: disable=no-member


class Signup:
    @add_rule_unauth(gui_consts.Signup.SignupEndpoint, methods=['POST', 'GET'])
    def process_signup(self):
        signup_collection = self._get_collection(gui_consts.Signup.SignupCollection)
        signup = signup_collection.find_one({})

        if request.method == 'GET':
            return jsonify({gui_consts.Signup.SignupField: bool(signup) or has_customer_login_happened()})

        # POST from here
        if signup or has_customer_login_happened():
            return return_error('Signup already completed', 400)

        signup_data = self.get_request_data_as_object() or {}

        new_password = signup_data[gui_consts.Signup.NewPassword] if \
            signup_data[gui_consts.Signup.ConfirmNewPassword] == signup_data[gui_consts.Signup.NewPassword] \
            else ''

        if not new_password:
            return return_error('Passwords do not match', 400)

        self._users_collection.update_one({'user_name': 'admin'},
                                          {'$set': {'password': bcrypt.hash(new_password)}})

        # we don't want to store creds openly
        signup_data[gui_consts.Signup.NewPassword] = ''
        signup_data[gui_consts.Signup.ConfirmNewPassword] = ''

        signup_collection.insert_one(signup_data)
        self._get_collection(CONFIGURABLE_CONFIGS_COLLECTION).update_one({
            'config_name': FeatureFlags.__name__
        }, {
            '$set': {
                f'config.{gui_consts.FeatureFlagsNames.TrialEnd}':
                    (datetime.now() + timedelta(days=30)).isoformat()[:10].replace('-', '/')
            }
        })

        # Reset this setting for new (version > 2.11) customers upon signup (Getting Started With Axonius Checklist)
        self._get_collection(CONFIGURABLE_CONFIGS_COLLECTION, CORE_UNIQUE_NAME).update_one({
            'config_name': CORE_CONFIG_NAME
        }, {
            '$set': {
                f'config.{gui_consts.GETTING_STARTED_CHECKLIST_SETTING}.enabled': True
            }
        })

        # Update Getting Started Checklist to interactive mode (version > 2.10)
        self._get_collection('getting_started', GUI_PLUGIN_NAME).update_one({}, {
            '$set': {
                'settings.interactive': True
            }
        })
        self._getting_started_settings['enabled'] = True
        return jsonify({})
