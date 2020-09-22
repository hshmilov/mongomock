# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from axonius.clients.azure.consts import AZURE_TENANT_ID
from axonius.entities import EntityType
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, get_count_incompliant_azure_cis_rule, \
    build_entities_query

logger = logging.getLogger(f'axonius.{__name__}')


class CISAzureCategory1:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()
        self._account_id = self._account_dict.get(AZURE_TENANT_ID) or 'unknown-tenant-id'

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

            # get count affected
            try:
                count_affected = get_count_incompliant_azure_cis_rule(
                    EntityType.Users,
                    rule_section,
                    account_id=self._account_id)
            except Exception as e:
                logger.debug(f'Error counting affected azure users for rule {rule_section}: {str(e)}')
                count_affected = 0

            # get affected users query
            try:
                users_query = build_entities_query(
                    'users',
                    rule_section,
                    account_id=self._account_id,
                    plugin_name='azure_ad_adapter',
                    field_prefix='azure'
                )
            except Exception as e:
                logger.debug(f'Error building query for affected azure users for rule '
                             f'{rule_section}: {str(e)}')
                users_query = None

            # add the rule
            self.report.add_rule(
                RuleStatus.Failed,
                rule_section,
                (len(errors), total_resources),
                count_affected,
                errors_to_gui(errors),
                users_query
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
        total_resources = 0

        for subscription_id, subscription_data in self.azure.all_subscriptions.items():
            subscription_name = subscription_data.get('displayName') or subscription_id

            all_roles = list(self.azure.rm_subscription_paginated_get(
                'providers/Microsoft.Authorization/roleDefinitions',
                subscription_id,
                api_version='2018-07-01'
            ))

            for role_raw in all_roles:
                role = role_raw.get('properties') or {}
                if role.get('type') != 'CustomRole':
                    continue

                total_resources += 1

                assignable_scopes = role.get('assignableScopes') or []
                permissions = role.get('permissions') or []
                # Check for entries with assignableScope of / or a subscription, and an action of *
                if any(x == '/' or x.startswith('/subscriptions') for x in assignable_scopes):
                    all_allowed = [action for permission in permissions for action in permission.get('actions', [])]
                    if '*' in all_allowed:
                        errors.append(
                            f'Found custom role "{role.get("roleName")}" in subscription "{subscription_name}" '
                            f'with "*" permissions, assigned to "{",".join(assignable_scopes)}"')

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
