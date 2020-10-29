import logging
import requests

from flask import (has_request_context, jsonify,
                   request, session, Response)

from axonius.plugin_base import random_string
from axonius.consts import gui_consts
from axonius.consts.gui_consts import (SIGNUP_TEST_COMPANY_NAME, CSRF_TOKEN_LENGTH,
                                       SIGNUP_TEST_CREDS, FeatureFlagsNames)
from axonius.types.enforcement_classes import TriggerPeriod
from axonius.utils.gui_helpers import (add_rule_unauth)
from axonius.utils.permissions_helper import is_axonius_role
from axonius.utils.serial_csv.constants import (MAX_ROWS_LEN, CELL_JOIN_DEFAULT)
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.routes.adapters.adapters import Adapters
from gui.routes.compliance.compliance import Compliance
from gui.routes.dashboard.dashboard import Dashboard
from gui.routes.enforcements.enforcements import Enforcements
from gui.routes.entities.entities import Entities
from gui.routes.instances.instances import Instances
from gui.routes.account.account import Account
from gui.routes.account.login import Login
from gui.routes.account.signup import Signup
from gui.routes.reports.reports import Reports
from gui.routes.settings.settings import Settings
from gui.routes.password_vault import PasswordVault
from gui.routes.labels.labels import Labels
from gui.routes.graphql.api import GraphQLAPI
# pylint: disable=no-member,invalid-name,no-self-use
from gui.routes.tunnel import Tunnel
from gui.routes.certificate import Certificate

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules()
class AppRoutes(Signup,
                Login,
                Account,
                Settings,
                Dashboard,
                Entities,
                Adapters,
                Enforcements,
                Reports,
                Compliance,
                Instances,
                PasswordVault,
                Labels,
                Certificate,
                Tunnel,
                GraphQLAPI):

    @gui_route_logged_in('get_constants', enforce_permissions=False)
    def get_constants(self):
        """
        Returns a dictionary between all string names and string values in the system.
        This is used to print "nice" spacted strings to the user while not using them as variable names

        path: /api/get_constants
        """

        def dictify_enum(e):
            return {r.name: r.value for r in e}

        constants = dict()
        order = [TriggerPeriod.all, TriggerPeriod.daily, TriggerPeriod.weekly, TriggerPeriod.monthly]
        constants['trigger_periods'] = [{x.name: x.value} for x in order]
        constants['csv_configs'] = {'max_rows': MAX_ROWS_LEN, 'cell_joiner': repr(CELL_JOIN_DEFAULT)}
        return jsonify(constants)

    @gui_route_logged_in('system/expired', enforce_session=False)
    def get_expiry_status(self):
        """
        Whether system has currently expired it's trial or contract.
        If no trial or contract expiration date, answer will be false.

        path: /api/system/expired
        """
        feature_flags_config = self.feature_flags_config()
        if feature_flags_config.get(FeatureFlagsNames.TrialEnd):
            return jsonify(self.trial_expired())
        if feature_flags_config.get(FeatureFlagsNames.ExpiryDate):
            return jsonify(self.contract_expired())
        return jsonify(False)

    @gui_route_logged_in('google_analytics/collect', methods=['GET', 'POST'], enforce_permissions=False)
    def google_analytics_proxy(self):
        """
        path: /api/google_analytics/collect
        """
        self.handle_ga_request('https://www.google-analytics.com/collect')
        return ''

    @gui_route_logged_in('google_analytics/r/collect', methods=['GET', 'POST'], enforce_permissions=False)
    def google_analytics_r_proxy(self):
        """
        path: /api/google_analytics/r/collect
        """
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
                if is_axonius_role(user):
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
        """
        path: /api/provision
        """
        return jsonify(self._maintenance_config.get('provision', True) or
                       self._maintenance_config.get('timeout') is not None)

    @add_rule_unauth('analytics')
    def get_analytics(self):
        """
        path: /api/analytics
        """
        return jsonify(self._maintenance_config.get('analytics', True) or
                       self._maintenance_config.get('timeout') is not None)

    @add_rule_unauth('troubleshooting')
    def get_troubleshooting(self):
        """
        path: /api/troubleshooting
        """
        return jsonify(self._maintenance_config.get('troubleshooting', True) or
                       self._maintenance_config.get('timeout') is not None)

    @gui_route_logged_in('csrf', methods=['GET'], enforce_permissions=False)
    # pylint: disable=no-self-use
    def csrf(self):
        """
        path: /api/csrf
        """
        if session and 'csrf-token' in session:
            session['csrf-token'] = random_string(CSRF_TOKEN_LENGTH)
            resp = Response(session['csrf-token'])
            resp.headers.add('X-CSRF-Token', session['csrf-token'])
            return resp
        return Response('')

    @add_rule_unauth('get_environment_name')
    def get_environment_name(self):
        """
        path: /api/get_environment_name
        """
        return jsonify({'environment_name': self._get_environment_name()})
