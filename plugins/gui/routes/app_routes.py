import logging

import requests
from flask import (has_request_context, jsonify,
                   request, session)

from axonius.consts import gui_consts
from axonius.consts.gui_consts import (SIGNUP_TEST_COMPANY_NAME,
                                       SIGNUP_TEST_CREDS)
from axonius.consts.plugin_consts import (AXONIUS_USER_NAME)
from axonius.types.enforcement_classes import TriggerPeriod
from axonius.utils.gui_helpers import (PermissionLevel,
                                       PermissionType, add_rule_unauth)
from gui.routes.adapters.adapters import Adapters
from gui.routes.compliance.compliance import Compliance
from gui.routes.dashboard.dashboard import Dashboard
from gui.routes.dashboard.notifications import Notifications
from gui.routes.enforcements.enforcements import Enforcements
from gui.routes.entities.entities import Entities
from gui.routes.instances.instances import Instances
from gui.routes.login.login import Login
from gui.routes.login.signup import Signup
from gui.routes.reports.reports import Reports
from gui.routes.settings.settings import Settings
from gui.routes.offline.configuration import Configuration
from gui.routes.password_vault import PasswordVault
# pylint: disable=no-member,invalid-name,no-self-use

logger = logging.getLogger(f'axonius.{__name__}')


class AppRoutes(Signup,
                Login,
                Settings,
                Dashboard,
                Entities,
                Adapters,
                Notifications,
                Enforcements,
                Reports,
                Compliance,
                Instances,
                Configuration,
                PasswordVault):

    @add_rule_unauth('get_constants')
    def get_constants(self):
        """
        Returns a dictionary between all string names and string values in the system.
        This is used to print "nice" spacted strings to the user while not using them as variable names
        """

        def dictify_enum(e):
            return {r.name: r.value for r in e}

        constants = dict()
        constants['permission_levels'] = dictify_enum(PermissionLevel)
        constants['permission_types'] = dictify_enum(PermissionType)
        order = [TriggerPeriod.all, TriggerPeriod.daily, TriggerPeriod.weekly, TriggerPeriod.monthly]
        constants['trigger_periods'] = [{x.name: x.value} for x in order]
        return jsonify(constants)

    @add_rule_unauth('google_analytics/collect', methods=['GET', 'POST'])
    def google_analytics_proxy(self):
        self.handle_ga_request('https://www.google-analytics.com/collect')
        return ''

    @add_rule_unauth('google_analytics/r/collect', methods=['GET', 'POST'])
    def google_analytics_r_proxy(self):
        self.handle_ga_request('https://www.google-analytics.com/r/collect')
        return ''

    def handle_ga_request(self, path):
        values = dict(request.values)
        signup_collection = self._get_collection(gui_consts.Signup.SignupCollection)
        signup = signup_collection.find_one({})
        if signup:
            customer = signup.get(gui_consts.Signup.CompanyField, 'company-not-set')
            if not customer \
                    or customer in [SIGNUP_TEST_CREDS[gui_consts.Signup.CompanyField], SIGNUP_TEST_COMPANY_NAME]:
                return

            if has_request_context():
                user = session.get('user')
                if user is None:
                    return
                user = dict(user)
                user_name = user.get('user_name')
                source = user.get('source')

                if user_name == AXONIUS_USER_NAME and source == 'internal':
                    return

            # referrer
            values['tid'] = 'UA-137924837-1'
            values['dr'] = f'https://{customer}'
            values['dh'] = customer
            if 'dl' in values:
                del values['dl']
            response = requests.request(request.method,
                                        path,
                                        params=values,
                                        timeout=(10, 30)
                                        )
            if response.status_code != 200:
                logger.error('Failed to submit ga data {response}')

    @add_rule_unauth('provision')
    def get_provision(self):
        if self.trial_expired() or self.contract_expired():
            return jsonify(True)

        return jsonify(self._maintenance_config.get('provision', False) or
                       self._maintenance_config.get('timeout') is not None)

    @add_rule_unauth('analytics')
    def get_analytics(self):
        if self.trial_expired() or self.contract_expired():
            return jsonify(True)

        return jsonify(self._maintenance_config.get('analytics', False) or
                       self._maintenance_config.get('timeout') is not None)

    @add_rule_unauth('troubleshooting')
    def get_troubleshooting(self):
        if self.trial_expired() or self.contract_expired():
            return jsonify(True)

        return jsonify(self._maintenance_config.get('troubleshooting', False) or
                       self._maintenance_config.get('timeout') is not None)

    @add_rule_unauth('get_environment_name')
    def get_environment_name(self):
        return jsonify({'environment_name': self._get_environment_name()})
