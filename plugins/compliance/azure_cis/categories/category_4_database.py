# pylint: disable=too-many-branches, too-many-nested-blocks
import logging
from collections import defaultdict

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, good_api_response, bad_api_response, get_api_error, \
    get_api_data

logger = logging.getLogger(f'axonius.{__name__}')


def get_azure_sql_servers(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = azure.sql_db.get_all_azure_sql_servers_for_subscription(subscription_id)
        except Exception as e:
            logger.exception('Exception while getting azure sql servers')
            return bad_api_response(f'Error getting sql servers '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.Sql/'
                                    f'servers?api-version=2015-05-01-preview): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


def get_azure_sql_servers_audit_settings(azure: AzureCloudConnection, sql_servers: dict) -> dict:
    error = get_api_error(sql_servers)
    if error:
        return bad_api_response(error)

    responses = get_api_data(sql_servers)

    settings_response = defaultdict(list)

    for subscription_name, response in responses.items():
        for server in response:
            try:
                url = server['id'].strip('/') + '/auditingSettings'
                response = azure.rm_get(url, '2017-03-01-preview')
                if 'value' not in response:
                    raise ValueError(f'No "value" in response')
                if not len(response['value']):
                    raise ValueError(f'Empty "value" list')
                if 'properties' not in response['value'][0]:
                    raise ValueError(f'No "properties" in value: {str(response["value"][0])}')

                settings_response[subscription_name].append(
                    {
                        'server': server,
                        'audit_settings': good_api_response(response['value'][0])
                    }
                )
            except Exception as e:
                error = f'Subscription {subscription_name!r}: can not get "auditingSettings" for ' \
                    f'server \'{server.get("name") or server.get("id")}\': {str(e)}'

                settings_response[subscription_name].append(
                    {
                        'server': server,
                        'audit_settings': bad_api_response(error)
                    }
                )

    return good_api_response(settings_response)


def get_azure_sql_servers_atp(azure: AzureCloudConnection, sql_servers: dict) -> dict:
    error = get_api_error(sql_servers)
    if error:
        return bad_api_response(error)

    responses = get_api_data(sql_servers)

    settings_response = defaultdict(list)

    for subscription_name, response in responses.items():
        for server in response:
            try:
                url = server['id'].strip('/') + '/securityAlertPolicies'
                response = azure.rm_get(url, '2017-03-01-preview')
                if 'value' not in response:
                    raise ValueError(f'No "value" in response')
                if not len(response['value']):
                    raise ValueError(f'Empty "value" list')
                if 'properties' not in response['value'][0]:
                    raise ValueError(f'No "properties" in value: {str(response["value"][0])}')

                settings_response[subscription_name].append(
                    {
                        'server': server,
                        'security_alert_policies': good_api_response(response['value'][0])
                    }
                )
            except Exception as e:
                error = f'Subscription {subscription_name!r}: can not get "securityAlertPolicies" for ' \
                    f'server \'{server.get("name") or server.get("id")}\': {str(e)}'

                settings_response[subscription_name].append(
                    {
                        'server': server,
                        'security_alert_policies': bad_api_response(error)
                    }
                )

    return good_api_response(settings_response)


def get_azure_mysql_servers(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = list(azure.rm_subscription_paginated_get(
                'providers/Microsoft.DBforMySQL/servers',
                subscription_id,
                api_version='2017-12-01'
            ))
        except Exception as e:
            logger.exception('Exception while getting azure mysql servers')
            return bad_api_response(f'Error getting sql servers '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.DBforMySQL/'
                                    f'servers?api-version=2017-12-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


def get_azure_postgresql_servers(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = list(azure.rm_subscription_paginated_get(
                'providers/Microsoft.DBforPostgreSQL/servers',
                subscription_id,
                api_version='2017-12-01'
            ))
            for server in response:
                try:
                    server_id = server['id'].strip('/')
                    all_configurations = list(azure.rm_paginated_get(f'{server_id}/configurations', '2017-12-01'))
                    all_configurations_by_name = {x['name']: x.get('properties') or {} for x in all_configurations}
                    server['extended_configurations'] = good_api_response(all_configurations_by_name)
                except Exception as e:
                    error = f'Subscription {subscription_name!r}: can not get postgres "/configurations" for ' \
                        f'server \'{server.get("name") or server.get("id")}\': {str(e)}'
                    server['extended_configurations'] = bad_api_response(error)
                    continue

        except Exception as e:
            logger.exception('Exception while getting azure postgresql servers')
            return bad_api_response(f'Error getting sql servers '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.DBforPostgreSQL/'
                                    f'servers?api-version=2017-12-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


class CISAzureCategory4:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()
        self._sql_servers = get_azure_sql_servers(azure)
        self._sql_servers_audit_settings = get_azure_sql_servers_audit_settings(azure, self._sql_servers)
        self._sql_servers_atp = get_azure_sql_servers_atp(azure, self._sql_servers)
        self._mysql_servers = get_azure_mysql_servers(azure)
        self._postgres_servers = get_azure_postgresql_servers(azure)

    @cis_rule('4.1')
    def check_cis_azure_4_1(self, **kwargs):
        """
        4.1 Ensure that 'Auditing' is set to 'On'
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._sql_servers_audit_settings)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers_audit_settings)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1

                server = server_dict['server']
                error = get_api_error(server_dict['audit_settings'])
                if error:
                    errors.append(error)
                    continue

                audit_settings = get_api_data(server_dict['audit_settings'])

                if str(audit_settings['properties'].get('state')).lower() != 'enabled':
                    errors.append(
                        f'Subscription {subscription_name!r}: server \'{server.get("name") or server["id"]}\' '
                        f'does not have auditing enabled'
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

    @cis_rule('4.2')
    def check_cis_azure_4_2(self, **kwargs):
        """
        4.2 Ensure that 'AuditActionGroups' in 'auditing' policy for a SQL server is set properly
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._sql_servers_audit_settings)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers_audit_settings)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1

                server = server_dict['server']
                error = get_api_error(server_dict['audit_settings'])
                if error:
                    errors.append(error)
                    continue

                audit_settings_properties = get_api_data(server_dict['audit_settings'])['properties']
                audit_actions_and_groups = [
                    x.upper().strip() for x in audit_settings_properties.get('auditActionsAndGroups') or []
                ]

                if not all(
                        x in audit_actions_and_groups for x in
                        [
                            'SUCCESSFUL_DATABASE_AUTHENTICATION_GROUP',
                            'FAILED_DATABASE_AUTHENTICATION_GROUP',
                            'BATCH_COMPLETED_GROUP'
                        ]
                ):
                    errors.append(
                        f'Subscription {subscription_name!r}: server \'{server.get("name") or server["id"]}\' '
                        f'AuditActionGroups is: {",".join(audit_actions_and_groups)}'
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

    @cis_rule('4.3')
    def check_cis_azure_4_3(self, **kwargs):
        """
        4.3 Ensure that 'Auditing' Retention is 'greater than 90 days'
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._sql_servers_audit_settings)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers_audit_settings)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1

                server = server_dict['server']
                error = get_api_error(server_dict['audit_settings'])
                if error:
                    errors.append(error)
                    continue

                audit_settings = get_api_data(server_dict['audit_settings'])
                retention_days = audit_settings['properties'].get('retentionDays') or -1

                if retention_days < 90:
                    errors.append(
                        f'Subscription {subscription_name!r}: server \'{server.get("name") or server["id"]}\' '
                        f'retention days value: {retention_days}'
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

    @cis_rule('4.4')
    def check_cis_azure_4_4(self, **kwargs):
        """
        4.4 Ensure that 'Advanced Data Security' on a SQL server is set to 'On'
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._sql_servers_atp)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers_atp)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1

                server = server_dict['server']
                error = get_api_error(server_dict['security_alert_policies'])
                if error:
                    errors.append(error)
                    continue

                audit_settings = get_api_data(server_dict['security_alert_policies'])
                state = str(audit_settings['properties'].get('state')).lower()

                if state != 'enabled':
                    errors.append(
                        f'Subscription {subscription_name!r}: server \'{server.get("name") or server["id"]}\' '
                        f'advanced data security is not enabled'
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

    @cis_rule('4.5')
    def check_cis_azure_4_5(self, **kwargs):
        """
        4.5 Ensure that 'Threat Detection types' is set to 'All'
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._sql_servers_atp)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers_atp)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1

                server = server_dict['server']
                error = get_api_error(server_dict['security_alert_policies'])
                if error:
                    errors.append(error)
                    continue

                audit_settings = get_api_data(server_dict['security_alert_policies'])
                disabled_alerts = audit_settings['properties'].get('disabledAlerts')

                if not isinstance(disabled_alerts, list) or len(disabled_alerts) > 0:
                    errors.append(
                        f'Subscription {subscription_name!r}: server \'{server.get("name") or server["id"]}\' '
                        f'Thread detection types excluded values: {",".join(disabled_alerts)}'
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

    @cis_rule('4.6')
    def check_cis_azure_4_6(self, **kwargs):
        """
        4.6 Ensure that 'Send alerts to' is set
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._sql_servers_atp)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers_atp)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1

                server = server_dict['server']
                error = get_api_error(server_dict['security_alert_policies'])
                if error:
                    errors.append(error)
                    continue

                audit_settings = get_api_data(server_dict['security_alert_policies'])
                email_addresses = audit_settings['properties'].get('emailAddresses')

                if not isinstance(email_addresses, list) or len([x for x in email_addresses if x]) == 0:
                    errors.append(
                        f'Subscription {subscription_name!r}: server \'{server.get("name") or server["id"]}\' '
                        f'does not have "send alerts to" configured'
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

    @cis_rule('4.7')
    def check_cis_azure_4_7(self, **kwargs):
        """
        4.7 Ensure that 'Email service and co-administrators' is 'Enabled'
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._sql_servers_atp)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers_atp)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1

                server = server_dict['server']
                error = get_api_error(server_dict['security_alert_policies'])
                if error:
                    errors.append(error)
                    continue

                audit_settings = get_api_data(server_dict['security_alert_policies'])
                email_account_admins = audit_settings['properties'].get('emailAccountAdmins')

                if not isinstance(email_account_admins, bool) or not email_account_admins:
                    errors.append(
                        f'Subscription {subscription_name!r}: server \'{server.get("name") or server["id"]}\' '
                        f'does not have the "Also send email notification to admins and subscription owners" option set'
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

    def check_sql_server_ad_administrators(self, rule_section):
        error = get_api_error(self._sql_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                try:
                    url = server_dict['id'].strip('/') + '/administrators'
                    does_have_ad_admin = False

                    for sql_server_admin in list(self.azure.rm_paginated_get(url, '2020-02-02-preview')):
                        properties = sql_server_admin.get('properties') or {}
                        if str(properties.get('administratorType')).lower() == 'activedirectory':
                            does_have_ad_admin = True
                            break

                    if not does_have_ad_admin:
                        errors.append(
                            f'Subscription {subscription_name!r}: '
                            f'server \'{server_dict.get("name") or server_dict["id"]}\' does not have AD administrators'
                        )
                        continue
                except Exception as e:
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server \'{server_dict.get("name") or server_dict["id"]}\' Exception: {str(e)}'
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

    @cis_rule('4.8')
    def check_cis_azure_4_8(self, **kwargs):
        """
        4.8 Ensure that Azure Active Directory Admin is configured
        """
        rule_section = kwargs['rule_section']
        self.check_sql_server_ad_administrators(rule_section)

    @cis_rule('4.9')
    def check_cis_azure_4_9(self, **kwargs):
        """
        4.9 Ensure that 'Data encryption' is set to 'On' on a SQL Database
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._sql_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers)
        total_resources = 0

        errors = []

        # For each subscription, for each server, get all dbs. for each db except default one, get tde status
        # pylint: disable=too-many-nested-blocks
        for subscription_name, response in responses.items():
            for server_dict in response:
                try:
                    url = server_dict['id'].strip('/') + '/databases'
                    for database in list(self.azure.rm_paginated_get(url, '2020-02-02-preview')):
                        db_name = database.get('name')
                        if db_name == 'master':
                            # default system DB, do not check
                            continue
                        total_resources += 1
                        url = database['id'].strip('/') + '/transparentDataEncryption'
                        result = self.azure.rm_get(url, '2017-03-01-preview')
                        try:
                            if not result.get('value'):
                                raise ValueError(f'Malformed result: {result}')
                            tde_status = (result['value'][0].get('properties') or {}).get('status')
                            if str(tde_status).lower() != 'enabled':
                                raise ValueError(f'Transparent Data Encryption is not enabled')
                        except Exception as e:
                            errors.append(
                                f'Subscription {subscription_name!r}: '
                                f'server \'{server_dict.get("name") or server_dict["id"]}\' '
                                f'db_name {db_name!r}: {str(e)}'
                            )
                            continue
                except Exception as e:
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server \'{server_dict.get("name") or server_dict["id"]}: Exception: {str(e)}'
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

    @cis_rule('4.10')
    def check_cis_azure_4_10(self, **kwargs):
        """
        4.10 Ensure SQL server's TDE protector is encrypted with BYOK (Use your own key)
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._sql_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._sql_servers)
        total_resources = 0

        errors = []

        # Notice that we do nto check the "5. Ensure Make selected key the default TDE protector is checked" value.
        # This is also not checked through the AWS CIS Foundations Benchmark pdf "Azure CLI" command, and I could
        # not find how to get it's value through the API.
        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                try:
                    url = server_dict['id'].strip('/') + '/encryptionProtector'
                    result = self.azure.rm_get(url, '2020-02-02-preview')
                    try:
                        if not result.get('value'):
                            raise ValueError(f'Malformed result: {result}')
                        value = result['value'][0]
                        properties = value.get('properties') or {}
                        if not (value.get('kind').lower() == 'azurekeyvault' and
                                properties.get('serverKeyType').lower() == 'azurekeyvault' and
                                properties.get('uri')):
                            raise ValueError(f'TDE protector is not encrypted with BYOK')
                    except Exception as e:
                        errors.append(
                            f'Subscription {subscription_name!r}: '
                            f'server \'{server_dict.get("name") or server_dict["id"]}\': {str(e)}'
                        )
                        continue
                except Exception as e:
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server \'{server_dict.get("name") or server_dict["id"]}\' Exception: {str(e)}'
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

    @cis_rule('4.11')
    def check_cis_azure_4_11(self, **kwargs):
        """
        4.11 Ensure 'Enforce SSL connection' is set to 'ENABLED' for MySQL Database Server
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._mysql_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._mysql_servers)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                server_name = server_dict.get('name') or server_dict.get('id')
                if str((server_dict.get('properties') or {}).get('sslEnforcement')).lower() != 'enabled':
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server {server_name!r}: ssl enforcement is disabled'
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

    @cis_rule('4.12')
    def check_cis_azure_4_12(self, **kwargs):
        """
        4.12 Ensure server parameter 'log_checkpoints' is set to 'ON' for PostgreSQL Database Server
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._postgres_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._postgres_servers)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                server_name = server_dict.get('name') or server_dict.get('id')

                error = get_api_error(server_dict['extended_configurations'])
                if error:
                    errors.append(error)
                    continue

                configurations_by_name = get_api_data(server_dict['extended_configurations'])
                if str((configurations_by_name.get('log_checkpoints') or {}).get('value')).lower() != 'on':
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server {server_name!r}: log_checkpoints is not set to "on"'
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

    @cis_rule('4.13')
    def check_cis_azure_4_13(self, **kwargs):
        """
        4.13 Ensure 'Enforce SSL connection' is set to 'ENABLED' for PostgreSQL Database Server
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._postgres_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._postgres_servers)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                server_name = server_dict.get('name') or server_dict.get('id')
                if str((server_dict.get('properties') or {}).get('sslEnforcement')).lower() != 'enabled':
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server {server_name!r}: ssl enforcement is disabled'
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

    @cis_rule('4.14')
    def check_cis_azure_4_14(self, **kwargs):
        """
        4.14 Ensure server parameter 'log_connections' is set to 'ON' for PostgreSQL Database Server
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._postgres_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._postgres_servers)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                server_name = server_dict.get('name') or server_dict.get('id')

                error = get_api_error(server_dict['extended_configurations'])
                if error:
                    errors.append(error)
                    continue

                configurations_by_name = get_api_data(server_dict['extended_configurations'])
                if str((configurations_by_name.get('log_connections') or {}).get('value')).lower() != 'on':
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server {server_name!r}: log_connections is not set to "on"'
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

    @cis_rule('4.15')
    def check_cis_azure_4_15(self, **kwargs):
        """
        4.15 Ensure server parameter 'log_disconnections' is set to 'ON' for PostgreSQL Database Server
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._postgres_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._postgres_servers)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                server_name = server_dict.get('name') or server_dict.get('id')

                error = get_api_error(server_dict['extended_configurations'])
                if error:
                    errors.append(error)
                    continue

                configurations_by_name = get_api_data(server_dict['extended_configurations'])
                if str((configurations_by_name.get('log_disconnections') or {}).get('value')).lower() != 'on':
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server {server_name!r}: log_disconnections is not set to "on"'
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

    @cis_rule('4.16')
    def check_cis_azure_4_16(self, **kwargs):
        """
        4.16 Ensure server parameter 'log_duration' is set to 'ON' for PostgreSQL Database Server
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._postgres_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._postgres_servers)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                server_name = server_dict.get('name') or server_dict.get('id')

                error = get_api_error(server_dict['extended_configurations'])
                if error:
                    errors.append(error)
                    continue

                configurations_by_name = get_api_data(server_dict['extended_configurations'])
                if str((configurations_by_name.get('log_duration') or {}).get('value')).lower() != 'on':
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server {server_name!r}: log_duration is not set to "on"'
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

    @cis_rule('4.17')
    def check_cis_azure_4_17(self, **kwargs):
        """
        4.17 Ensure server parameter 'connection_throttling' is set to 'ON' for PostgreSQL Database Server
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._postgres_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._postgres_servers)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                server_name = server_dict.get('name') or server_dict.get('id')

                error = get_api_error(server_dict['extended_configurations'])
                if error:
                    errors.append(error)
                    continue

                configurations_by_name = get_api_data(server_dict['extended_configurations'])
                if str((configurations_by_name.get('connection_throttling') or {}).get('value')).lower() != 'on':
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server {server_name!r}: connection_throttling is not set to "on"'
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

    @cis_rule('4.18')
    def check_cis_azure_4_18(self, **kwargs):
        """
        4.18 Ensure server parameter 'log_retention_days' is greater than 3 days for PostgreSQL Database Server
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._postgres_servers)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._postgres_servers)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            for server_dict in response:
                total_resources += 1
                server_name = server_dict.get('name') or server_dict.get('id')

                error = get_api_error(server_dict['extended_configurations'])
                if error:
                    errors.append(error)
                    continue

                configurations_by_name = get_api_data(server_dict['extended_configurations'])
                retention_days = (configurations_by_name.get('log_retention_days') or {}).get('value')
                try:
                    retention_days = int(retention_days)
                    assert retention_days > 3
                except Exception:
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'server {server_name!r}: log_retention_days is {retention_days}'
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

    @cis_rule('4.19')
    def check_cis_azure_4_19(self, **kwargs):
        """
        4.19 Ensure that Azure Active Directory Admin is configured
        """
        rule_section = kwargs['rule_section']
        self.check_sql_server_ad_administrators(rule_section)
