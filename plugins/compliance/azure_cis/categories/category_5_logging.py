# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, bad_api_response, good_api_response, get_api_error, \
    get_api_data

logger = logging.getLogger(f'axonius.{__name__}')


def get_activity_log_profiles(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = list(azure.rm_subscription_paginated_get(
                'providers/microsoft.insights/logprofiles',
                subscription_id,
                api_version='2016-03-01'
            ))
        except Exception as e:
            logger.exception('Exception while getting activity log profiles')
            return bad_api_response(f'Error getting activity log profiles'
                                    f'(/subscription/{subscription_id}/providers/microsoft.insights/'
                                    f'logprofiles?api-version=2016-03-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


def get_activity_log_alerts(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = list(azure.rm_subscription_paginated_get(
                'providers/microsoft.insights/activityLogAlerts',
                subscription_id,
                api_version='2017-04-01'
            ))
        except Exception as e:
            logger.exception('Exception while getting azure sql servers')
            return bad_api_response(f'Error getting sql servers '
                                    f'(/subscription/{subscription_id}/providers/microsoft.insights/'
                                    f'activityLogAlerts?api-version=2017-04-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


class CISAzureCategory5:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()
        self._activity_log_profiles = get_activity_log_profiles(azure)
        self._activity_log_alerts = get_activity_log_alerts(azure)

    @cis_rule('5.1.1')
    def check_cis_azure_5_1_1(self, **kwargs):
        """
        5.1.1 Ensure that a Log Profile exists
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._activity_log_profiles)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._activity_log_profiles)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            total_resources += 1
            if not response:
                errors.append(
                    f'Subscription {subscription_name!r}: No activity log'
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

    @cis_rule('5.1.2')
    def check_cis_azure_5_1_2(self, **kwargs):
        """
        5.1.2 Ensure that Activity Log Retention is set 365 days or greater
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._activity_log_profiles)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._activity_log_profiles)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            total_resources += 1
            if not isinstance(response, list) or not response:
                errors.append(
                    f'Subscription {subscription_name!r}: No activity log'
                )
                continue

            activity_log_properties = response[0].get('properties') or {}
            retention_policy = activity_log_properties.get('retentionPolicy') or {}
            try:
                enabled = retention_policy.get('enabled')
                days = retention_policy.get('days')

                if not enabled and not days:
                    continue

                if enabled and days >= 365:
                    continue

                raise ValueError(f'Retention policy is set to {days} days (enablement status: {enabled})')
            except Exception as e:
                errors.append(
                    f'Subscription {subscription_name!r}: {str(e)}'
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

    @cis_rule('5.1.3')
    def check_cis_azure_5_1_3(self, **kwargs):
        """
        5.1.3 Ensure audit profile captures all the activities
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._activity_log_profiles)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._activity_log_profiles)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            total_resources += 1
            if not isinstance(response, list) or not response:
                errors.append(
                    f'Subscription {subscription_name!r}: No activity log'
                )
                continue

            activity_log_properties = response[0].get('properties') or {}
            categories = [x.lower().strip() for x in activity_log_properties.get('categories') or []]
            if not all(x in categories for x in ['write', 'delete', 'action']):
                errors.append(
                    f'Subscription {subscription_name!r}: Partial categories: {",".join(categories)!r}'
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

    @cis_rule('5.1.4')
    def check_cis_azure_5_1_4(self, **kwargs):
        """
        5.1.4 Ensure the log profile captures activity logs for all regions including global
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._activity_log_profiles)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._activity_log_profiles)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            total_resources += 1
            try:
                subscription_id = self.azure.get_subscription_id_by_subscription_name(subscription_name)
                if not subscription_id:
                    subscription_id = subscription_name

                all_account_locations = [
                    x['name'].lower().strip()
                    for x in self.azure.rm_subscription_paginated_get('locations', subscription_id, '2016-06-01')
                ]
            except Exception as e:
                errors.append(
                    f'Subscription {subscription_name!r}: could not get subscription '
                    f'locations ("/locations?api-version=2016-06-01"): {str(e)}'
                )
                continue

            if not isinstance(response, list) or not response:
                errors.append(
                    f'Subscription {subscription_name!r}: No activity log'
                )
                continue

            activity_log_properties = response[0].get('properties') or {}
            locations = [x.lower().strip() for x in activity_log_properties.get('locations') or []]
            if not all(x in locations for x in all_account_locations):
                errors.append(
                    f'Subscription {subscription_name!r}: '
                    f'Partial locations: {",".join(locations)!r}, should be: {",".join(all_account_locations)!r}'
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

    @cis_rule('5.1.5')
    def check_cis_azure_5_1_5(self, **kwargs):
        """
        5.1.5 Ensure the storage container storing the activity logs is not publicly accessible
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._activity_log_profiles)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._activity_log_profiles)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            total_resources += 1
            if not isinstance(response, list) or not response:
                errors.append(
                    f'Subscription {subscription_name!r}: No activity log'
                )
                continue

            activity_log_properties = response[0].get('properties') or {}
            storage_account_id = activity_log_properties.get('storageAccountId')
            if not storage_account_id:
                errors.append(
                    f'Subscription {subscription_name!r}: No storage account configured'
                )
                continue

            try:
                try:
                    response = list(
                        self.azure.rm_paginated_get(
                            f'{storage_account_id.strip("/")}/blobServices/default/containers',
                            '2019-06-01'
                        )
                    )
                except Exception as c:
                    raise ValueError(f'Problem querying for storage container: {str(c)}')

                if not isinstance(response, list) or not response:
                    raise ValueError(f'Invalid response: {response}')

                insights_operational_logs_blob = [
                    x for x in response if x['name'].lower().strip() == 'insights-operational-logs'
                ]

                if not insights_operational_logs_blob:
                    raise ValueError(f'container \'insights-operational-logs\' does not exist')

                insights_operational_logs_blob = insights_operational_logs_blob[0]

                if str((insights_operational_logs_blob.get('properties') or {}).get('publicAccess')).lower() != 'none':
                    raise ValueError(f'container \'insights_operational_logs_blob\' '
                                     f'inside the activity log associated storage account is public')

            except Exception as e:
                errors.append(
                    f'Subscription {subscription_name!r}: {str(e)}'
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

    @cis_rule('5.1.6')
    def check_cis_azure_5_1_6(self, **kwargs):
        """
        5.1.6 Ensure the storage account containing the container with activity logs is
        encrypted with BYOK (Use Your Own Key)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._activity_log_profiles)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._activity_log_profiles)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            total_resources += 1
            if not isinstance(response, list) or not response:
                errors.append(
                    f'Subscription {subscription_name!r}: No activity log'
                )
                continue

            activity_log_properties = response[0].get('properties') or {}
            storage_account_id = activity_log_properties.get('storageAccountId')
            if not storage_account_id:
                errors.append(
                    f'Subscription {subscription_name!r}: No storage account configured'
                )
                continue

            try:
                try:
                    subscription_id = self.azure.get_subscription_id_by_subscription_name(subscription_name)
                    if not subscription_id:
                        subscription_id = subscription_name

                    all_storage_accounts = self.azure.storage.get_all_storage_accounts_for_subscription(
                        subscription_id
                    )

                    storage_account = [
                        x for x in all_storage_accounts if x['id'].lower() == str(storage_account_id).lower()
                    ]
                    if not storage_account:
                        raise ValueError(f'Could not find the associated storage account {storage_account_id!r}')
                    storage_account = storage_account[0]
                except Exception as c:
                    raise ValueError(f'Problem querying storage account: {str(c)}')
                encryption = (storage_account.get('properties') or {}).get('encryption') or {}
                key_source = str(encryption.get('keySource')).lower().strip()
                key_vault_properties = encryption.get('keyVaultProperties') or encryption.get('keyvaultproperties')

                if key_source != 'microsoft.keyvault' or not key_vault_properties:
                    raise ValueError(
                        f'The storage account {storage_account.get("name")!r} associated with this activity log '
                        f'is not encrypted with BYOK'
                    )
            except Exception as e:
                errors.append(
                    f'Subscription {subscription_name!r}: {str(e)}'
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

    # pylint: disable=too-many-branches, too-many-nested-blocks
    @cis_rule('5.1.7')
    def check_cis_azure_5_1_7(self, **kwargs):
        """
        5.1.7 Ensure that logging for Azure KeyVault is 'Enabled'
        """
        rule_section = kwargs['rule_section']
        total_resources = 0
        errors = []

        for subscription_id, subscription_data in self.azure.all_subscriptions.items():
            subscription_name = subscription_data.get('displayName') or subscription_id
            try:
                all_keyvaults = self.azure.keyvault.get_all_azure_keyvaults_for_subscription(subscription_id)
            except Exception as e:
                self.report.add_rule_error(
                    f'Could not get all keyvaults for subscription {subscription_name!r}: {str(e)}'
                )
                return

            for keyvault in all_keyvaults:
                total_resources += 1
                try:
                    url = keyvault['id'].strip('/') + '/providers/microsoft.insights/diagnosticSettings'
                    res = list(self.azure.rm_paginated_get(url, '2017-05-01-preview'))
                    if not res:
                        raise ValueError(f'No logging enabled for keyvault {keyvault["name"]!r}')

                    did_find_one_valid = False
                    for diagnostic_setting in res:
                        properties = diagnostic_setting.get('properties') or {}
                        if not properties.get('storageAccountId'):
                            continue

                        for log in (properties.get('logs') or []):
                            if str(log.get('category')).lower().strip() == 'auditevent' and log.get('enabled'):
                                retention_policy = log.get('retentionPolicy') or {}
                                if retention_policy.get('enabled') is False and retention_policy.get('days') == 0:
                                    # save forever
                                    did_find_one_valid = True
                                    break

                                if retention_policy.get('enabled') and retention_policy.get('days') >= 180:
                                    did_find_one_valid = True
                                    break

                        if did_find_one_valid:
                            break

                    if not did_find_one_valid:
                        raise ValueError(f'Invalid diagnostic settings for keyvault {keyvault["name"]!r}')
                except Exception as e:
                    errors.append(
                        f'Subscription {subscription_name!r}: {str(e)}'
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

    def check_5_2_metric(self, rule_section: str, operation_name: str):
        error = get_api_error(self._activity_log_alerts)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._activity_log_alerts)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            total_resources += 1
            did_find = False
            try:
                for alert in response:
                    properties = alert.get('properties') or {}
                    alert_location = str(alert.get('location')).lower()
                    alert_enabled = properties.get('enabled')
                    alert_condition = properties.get('condition')
                    alert_scopes = properties.get('scopes') or []

                    subscription_id = self.azure.get_subscription_id_by_subscription_name(subscription_name)
                    if not subscription_id:
                        subscription_id = subscription_name

                    if alert_enabled is True and alert_location == 'global' and any(
                            [f'/subscriptions/{subscription_id}' == x.rstrip('/').lower() for x in alert_scopes]
                    ):
                        for condition in (alert_condition.get('allOf') or []):
                            if condition.get('field', '') == 'operationName' and \
                                    condition.get('equals', '').lower() == operation_name and \
                                    not condition.get('containsAny'):
                                did_find = True

            except Exception as e:
                errors.append(
                    f'Subscription {subscription_name!r}: {str(e)}'
                )
                continue

            if not did_find:
                errors.append(
                    f'Subscription {subscription_name!r}: Did not find a valid configured '
                    f'alert for operation {operation_name!r}'
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

    @cis_rule('5.2.1')
    def check_cis_azure_5_2_1(self, **kwargs):
        """
        5.2.1 Ensure that Activity Log Alert exists for Create Policy Assignment
        """
        rule_section = kwargs['rule_section']
        self.check_5_2_metric(rule_section, 'microsoft.authorization/policyassignments/write')

    @cis_rule('5.2.2')
    def check_cis_azure_5_2_2(self, **kwargs):
        """
        5.2.2 Ensure that Activity Log Alert exists for Create or Update Network Security Group
        """
        rule_section = kwargs['rule_section']
        self.check_5_2_metric(rule_section, 'microsoft.network/networksecuritygroups/write')

    @cis_rule('5.2.3')
    def check_cis_azure_5_2_3(self, **kwargs):
        """
        5.2.3 Ensure that Activity Log Alert exists for Delete Network Security Group
        """
        rule_section = kwargs['rule_section']
        self.check_5_2_metric(rule_section, 'microsoft.network/networksecuritygroups/delete')

    @cis_rule('5.2.4')
    def check_cis_azure_5_2_4(self, **kwargs):
        """
        5.2.4 Ensure that Activity Log Alert exists for Create or Update Network Security Group Rule
        """
        rule_section = kwargs['rule_section']
        self.check_5_2_metric(rule_section, 'microsoft.network/networksecuritygroups/securityrules/write')

    @cis_rule('5.2.5')
    def check_cis_azure_5_2_5(self, **kwargs):
        """
        5.2.5 Ensure that activity log alert exists for the Delete Network Security Group Rule
        """
        rule_section = kwargs['rule_section']
        self.check_5_2_metric(rule_section, 'microsoft.network/networksecuritygroups/securityrules/delete"')

    @cis_rule('5.2.6')
    def check_cis_azure_5_2_6(self, **kwargs):
        """
        5.2.6 Ensure that Activity Log Alert exists for Create or Update Security Solution
        """
        rule_section = kwargs['rule_section']
        self.check_5_2_metric(rule_section, 'microsoft.security/securitysolutions/write')

    @cis_rule('5.2.7')
    def check_cis_azure_5_2_7(self, **kwargs):
        """
        5.2.7 Ensure that Activity Log Alert exists for Delete Security Solution
        """
        rule_section = kwargs['rule_section']
        self.check_5_2_metric(rule_section, 'microsoft.security/securitysolutions/delete')

    @cis_rule('5.2.8')
    def check_cis_azure_5_2_8(self, **kwargs):
        """
        5.2.8 Ensure that Activity Log Alert exists for Create or Update or Delete SQL Server Firewall Rule
        """
        rule_section = kwargs['rule_section']
        self.check_5_2_metric(rule_section, '"microsoft.sql/servers/firewallrules/write')

    @cis_rule('5.2.9')
    def check_cis_azure_5_2_9(self, **kwargs):
        """
        5.2.9 Ensure that Activity Log Alert exists for Update Security Policy
        """
        rule_section = kwargs['rule_section']
        self.check_5_2_metric(rule_section, 'microsoft.security/policies/write')
