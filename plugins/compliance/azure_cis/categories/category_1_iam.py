# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui

logger = logging.getLogger(f'axonius.{__name__}')


class CISAzureCategory1:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()

    @cis_rule('1.3')
    def check_cis_azure_1_3(self, **kwargs):
        """
        1.3 Ensure that there are no guest users
        """
        rule_section = kwargs['rule_section']
        total_resources = self.azure.ad.get_total_users_count()
        errors = []

        for guest_user in self.azure.graph_paginated_get(
                'users',
                api_filter='userType eq \'Guest\'',
                api_select='displayName,mail'
        ):
            display_name = guest_user.get('displayName', '')
            mail = guest_user.get('mail', '')

            errors.append(f'Found guest user "{display_name}" ({mail})')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                len(errors),
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )

    @cis_rule('1.23')
    def check_cis_azure_1_23(self, **kwargs):
        """
        1.23 Ensure that no custom subscription owner roles are created
        """
        rule_section = kwargs['rule_section']
        errors = []

        all_roles = list(self.azure.rm_subscription_paginated_get(
            'providers/Microsoft.Authorization/roleDefinitions',
            api_version='2018-07-01'
        ))
        total_resources = len(all_roles)

        for role_raw in all_roles:
            role = role_raw.get('properties') or {}
            if role.get('type') != 'CustomRole':
                continue

            assignable_scopes = role.get('assignableScopes') or []
            permissions = role.get('permissions') or []
            # Check for entries with assignableScope of / or a subscription, and an action of *
            if any(x == '/' or x.startswith('/subscriptions') for x in assignable_scopes):
                all_allowed = [action for permission in permissions for action in permission.get('actions', [])]
                if '*' in all_allowed:
                    errors.append(f'Found custom role "{role.get("roleName")}" with "*" permissions '
                                  f'assigned to "{",".join(assignable_scopes)}"')

        if errors:
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                0,
                errors_to_gui(errors)
            )
        else:
            self.report.add_rule(
                RuleStatus.Passed,
                rule_section,
                (0, total_resources),
                0,
                ''
            )
