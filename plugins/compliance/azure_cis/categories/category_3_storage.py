# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, bad_api_response, good_api_response, get_api_error, \
    get_api_data

logger = logging.getLogger(f'axonius.{__name__}')


def get_all_storage_accounts(azure):
    results = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = list(azure.storage.get_all_storage_accounts_for_subscription(subscription_id))
            results[subscription_name] = response
        except Exception as e:
            logger.exception('Exception while getting storage accounts')
            return bad_api_response(f'Error getting Security Center storage accounts '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.Storage/storageAccounts/'
                                    f'?api-version=2019-06-01): {str(e)}')

    return good_api_response(results)


class CISAzureCategory3:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()
        self._all_storage_accounts = get_all_storage_accounts(azure)

    @cis_rule('3.1')
    def check_cis_azure_3_1(self, **kwargs):
        """
        3.1 Ensure that 'Secure transfer required' is set to 'Enabled'
        """
        rule_section = kwargs['rule_section']
        total_resources = 0
        errors = []

        error = get_api_error(self._all_storage_accounts)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_storage_accounts = get_api_data(self._all_storage_accounts)

        for subscription_name, response in all_storage_accounts.items():
            total_resources += len(response)
            for storage_account in response:
                if storage_account.get('properties', {}).get('supportsHttpsTrafficOnly') is not True:
                    errors.append(
                        f'Subscription "{subscription_name}": '
                        f'Storage Account "{storage_account.get("name") or storage_account.get("id")}" Does not have'
                        f'"Secure transfer required" set to "Enabled"'
                    )

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

    @cis_rule('3.6')
    def check_cis_azure_3_6(self, **kwargs):
        """
        3.6 Ensure that 'Public access level' is set to Private for blob containers
        """
        rule_section = kwargs['rule_section']
        total_resources = 0
        errors = []

        error = get_api_error(self._all_storage_accounts)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_storage_accounts = get_api_data(self._all_storage_accounts)

        for subscription_name, response in all_storage_accounts.items():
            for storage_account in response:
                storage_account_id = storage_account['id']
                storage_account_name = storage_account.get('name') or storage_account.get('id')
                all_containers = list(
                    self.azure.rm_paginated_get(
                        f'{storage_account_id.lstrip("/")}/blobServices/default/containers',
                        api_version='2019-06-01'
                    )
                )

                total_resources += len(all_containers)

                for container in all_containers:
                    container_name = container.get('name') or container.get('id')
                    container_properties = container.get('properties') or {}
                    if container_properties.get('deleted') is True:
                        continue
                    public_access = container_properties.get('publicAccess')
                    if public_access is None:
                        errors.append(
                            f'Subscription "{subscription_name}": Storage account "{storage_account_name}" '
                            f'has container "{container_name}" with no publicAccess data'
                        )
                        continue
                    if str(public_access).lower() != 'none':
                        errors.append(
                            f'Subscription "{subscription_name}": Storage account "{storage_account_name}" '
                            f'has container "{container_name}" with public access level set to "{public_access}"'
                        )
                        continue

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

    @cis_rule('3.7')
    def check_cis_azure_3_7(self, **kwargs):
        """
        3.7 Ensure that 'Public access level' is set to Private for blob containers
        """
        rule_section = kwargs['rule_section']
        total_resources = 0
        errors = []

        error = get_api_error(self._all_storage_accounts)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_storage_accounts = get_api_data(self._all_storage_accounts)

        for subscription_name, response in all_storage_accounts.items():
            total_resources += len(response)
            for storage_account in response:
                sa_properties = storage_account.get('properties', {})
                storage_account_network_acl_default_action = sa_properties.get('networkAcls', {}).get('defaultAction')
                if str(storage_account_network_acl_default_action).lower() != 'deny':
                    errors.append(
                        f'Subscription "{subscription_name}": '
                        f'Storage Account "{storage_account.get("name") or storage_account.get("id")}" '
                        f'default action is "{storage_account_network_acl_default_action}"'
                    )

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
