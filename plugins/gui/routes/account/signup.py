from datetime import datetime, timedelta

from flask import (jsonify,
                   request)

from axonius.consts import gui_consts
from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.plugin_consts import GUI_PLUGIN_NAME
from axonius.plugin_base import return_error
from axonius.utils.hash import user_password_handler
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.feature_flags import FeatureFlags
from gui.logic.login_helper import has_customer_login_happened
# pylint: disable=no-member


@gui_category_add_rules(gui_consts.Signup.SignupEndpoint)
class Signup:
    @gui_route_logged_in(methods=['POST', 'GET'], enforce_session=False)
    def process_signup(self):
        """
        Process initial signup.

        path: /api/signup
        """
        return self._process_signup()

    # pylint: disable=dangerous-default-value
    def _process_signup(self, manual_signup: dict = {}):
        """Process initial signup."""
        signup_collection = self._get_collection(gui_consts.Signup.SignupCollection)
        signup = signup_collection.find_one({})

        if not manual_signup and request.method == 'GET':
            return jsonify({gui_consts.Signup.SignupField: bool(signup) or has_customer_login_happened()})

        # POST from here
        if signup or has_customer_login_happened():
            if manual_signup:
                return False
            return return_error('Signup already completed', 400)

        if manual_signup:
            signup_data = manual_signup
        else:
            signup_data = self.get_request_data_as_object() or {}

        new_password = signup_data[gui_consts.Signup.NewPassword] if \
            signup_data[gui_consts.Signup.ConfirmNewPassword] == signup_data[gui_consts.Signup.NewPassword] \
            else ''

        if not new_password:
            return return_error('Passwords do not match', 400)

        password, salt = user_password_handler(new_password)
        self._users_collection.update_one({'user_name': 'admin'},
                                          {'$set': {'password': password, 'salt': salt,
                                                    'email': signup_data.get(gui_consts.Signup.ContactEmailField)}})

        # we don't want to store creds openly
        signup_data[gui_consts.Signup.NewPassword] = ''
        signup_data[gui_consts.Signup.ConfirmNewPassword] = ''

        signup_collection.insert_one(signup_data)

        feature_flags = self.plugins.gui.configurable_configs[FeatureFlags.__name__]
        if not feature_flags or \
                (isinstance(feature_flags, dict) and feature_flags.get(gui_consts.FeatureFlagsNames.TrialEnd) != ''):
            self.plugins.gui.configurable_configs.update_config(
                FeatureFlags.__name__,
                {
                    gui_consts.FeatureFlagsNames.TrialEnd:
                        (datetime.now() + timedelta(days=30)).isoformat()[:10].replace('-', '/')
                }
            )

        # Reset this setting for new (version > 2.11) customers upon signup (Getting Started With Axonius Checklist)
        self.plugins.core.configurable_configs.update_config(
            CORE_CONFIG_NAME,
            {f'{gui_consts.GETTING_STARTED_CHECKLIST_SETTING}.enabled': True}
        )

        # Update Getting Started Checklist to interactive mode (version > 2.10)
        self._get_collection('getting_started', GUI_PLUGIN_NAME).update_one({}, {
            '$set': {
                'settings.interactive': True
            }
        })
        self._getting_started_settings['enabled'] = True

        if manual_signup:
            return True

        result = {}
        api_keys = signup_data.get(gui_consts.Signup.ApiKeysField)
        if api_keys:
            user_from_db = self._users_collection.find_one({'user_name': 'admin'})
            result['api_key'] = user_from_db['api_key']
            result['api_secret'] = user_from_db['api_secret']

        return jsonify(result)
