# pylint: disable=too-many-branches, too-many-nested-blocks, too-many-locals
import logging
import socket
import struct

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, bad_api_response, good_api_response, get_api_error, \
    get_api_data

logger = logging.getLogger(f'axonius.{__name__}')


def get_network_security_groups(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = list(azure.rm_subscription_paginated_get(
                'providers/Microsoft.Network/networkSecurityGroups',
                subscription_id,
                api_version='2020-05-01'
            ))
        except Exception as e:
            logger.exception('Exception while getting network security groups')
            return bad_api_response(f'Error getting network security groups '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.Network/'
                                    f'networkSecurityGroups?api-version=2020-05-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


# pylint: disable=too-many-branches, too-many-nested-blocks, too-many-locals
class CISAzureCategory6:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()
        self._network_security_groups = get_network_security_groups(azure)

    def check_inbound_nsg(self, rule_section: str, port: int):
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-locals
        error = get_api_error(self._network_security_groups)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._network_security_groups)
        total_resources = 0

        errors = []

        port_str = str(port)

        # pylint: disable=too-many-branches, too-many-nested-blocks, too-many-locals
        for subscription_name, response in responses.items():
            for nsg in response:
                total_resources += 1
                nsg_name = nsg.get('name') or 'Unknown'
                rules = (nsg.get('properties') or {}).get('securityRules') or []
                bad_rules_per_nsg = []
                for rule in rules:
                    rule_name = rule.get('name') or 'Unknown'
                    properties = rule.get('properties') or {}
                    rule_access = str(properties.get('access')).lower()
                    rule_direction = str(properties.get('direction')).lower()
                    rule_protocol = str(properties.get('protocol')).lower()
                    rule_destination = str(properties.get('destinationPortRange')).lower()
                    rule_destination_list = [str(x).lower() for x in properties.get('destinationPortRanges') or []]
                    rule_source_address = str(properties.get('sourceAddressPrefix')).lower()
                    rule_source_address_list = [str(x).lower() for x in properties.get('sourceAddressPrefix') or []]

                    rule_destination_match = False
                    if rule_access == 'allow' and rule_direction == 'inbound' and rule_protocol in ['tcp', '*']:
                        if rule_destination == '*' or rule_destination == port_str or port_str in rule_destination_list:
                            rule_destination_match = True
                        else:
                            for rule_port_range in rule_destination_list + [rule_destination]:
                                if '-' in rule_port_range:
                                    try:
                                        from_port, to_port = rule_port_range.split('-')
                                        if int(from_port) <= port <= int(to_port):
                                            rule_destination_match = True
                                            break
                                    except Exception:
                                        logger.exception(f'Failed parsing port range {rule_port_range!r}')

                        if rule_destination_match:
                            all_destination_rules = rule_source_address_list + [rule_source_address]
                            if any(
                                    ('/0' in dest_rule or dest_rule in ['*', '0.0.0.0', 'internet', 'any'])
                                    for dest_rule in all_destination_rules
                            ):
                                bad_rules_per_nsg.append(rule_name)

                if bad_rules_per_nsg:
                    errors.append(
                        f'Subscription "{subscription_name}": Network Security Group {nsg_name!r} has '
                        f'rules that allow port {port} from the entire internet: {",".join(bad_rules_per_nsg)}'
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

    @cis_rule('6.1')
    def check_cis_azure_6_1(self, **kwargs):
        """
        6.1 Ensure that RDP access is restricted from the internet
        """
        self.check_inbound_nsg(kwargs['rule_section'], 3389)

    @cis_rule('6.2')
    def check_cis_azure_6_2(self, **kwargs):
        """
        6.2 Ensure that SSH access is restricted from the internet
        """
        self.check_inbound_nsg(kwargs['rule_section'], 22)

    @cis_rule('6.3')
    def check_cis_azure_6_3(self, **kwargs):
        """
        6.3 Ensure no SQL Databases allow ingress 0.0.0.0/0 (ANY IP)
        """
        rule_section = kwargs['rule_section']
        total_resources = 0
        errors = []

        for subscription_id, subscription_data in self.azure.all_subscriptions.items():
            subscription_name = subscription_data.get('displayName') or subscription_id

            try:
                sql_servers_for_subscription = self.azure.sql_db.get_all_azure_sql_servers_for_subscription(
                    subscription_id
                )
            except Exception as e:
                logger.exception('Exception while getting azure sql servers')
                errors.append(
                    f'Subscription {subscription_name!r}: '
                    f'Error getting sql servers (/subscription/{subscription_id}/providers/Microsoft.Sql/'
                    f'servers?api-version=2015-05-01-preview): {str(e)}')
                # In case of a failed subscription we add to resources 1, and not the amount of fw
                total_resources += 1
                continue

            for sql_server in sql_servers_for_subscription:
                if 'id' not in sql_server:
                    logger.warning(f'Warning: no id in sql server {sql_server}')
                    continue

                total_resources += 1

                url = sql_server['id'].strip('/') + '/firewallRules'
                sql_server_name = sql_server.get('name') or sql_server['id']
                try:
                    all_firwall_rules_for_sql_server = self.azure.rm_paginated_get(url, '2017-03-01-preview')
                except Exception as e:
                    logger.exception('Exception while getting azure sql servers firewall rules')
                    errors.append(
                        f'Subscription {subscription_name!r}: '
                        f'Error getting sql servers firewall rules ({url!r}): {str(e)}')
                    continue

                try:
                    for fw_rule in all_firwall_rules_for_sql_server:
                        properties = fw_rule.get('properties') or {}
                        start_ip_address = properties.get('startIpAddress')
                        end_ip_address = properties.get('endIpAddress')
                        if not start_ip_address or not end_ip_address:
                            raise ValueError(f'Malformed firewall {fw_rule.get("name")} - no start or end ip addresses')

                        try:
                            start_ip_address_as_int = struct.unpack('!I', socket.inet_aton(start_ip_address))[0]
                            end_ip_address_as_int = struct.unpack('!I', socket.inet_aton(end_ip_address))[0]
                        except Exception:
                            raise ValueError(
                                f'Malformed firewall {fw_rule.get("name")} - invalid start or end ip addresses')

                        # The azure CIS documentation does not specify what is the criteria for
                        # 'all the internet', it asks to ensure it doesn't have 'Any other combination which allows
                        # access to wider public IP ranges'.
                        # also, checking if start_ip_address is 0.0.0.0 is not good because sometimes there are rules
                        # that allow access from 0.0.0.0 to 0.0.0.0 (valid).
                        # so this is something i came up with:
                        if (end_ip_address_as_int - start_ip_address_as_int) > 2 ** 30:
                            raise ValueError(f'Firewall rule with too '
                                             f'wide range: {start_ip_address} - {end_ip_address}')

                except Exception as e:
                    logger.exception('Exception while parsing azure sql servers firewall rules')
                    errors.append(f'Subscription {subscription_name!r}, SQL Server {sql_server_name!r}: {str(e)}')
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

    @cis_rule('6.4')
    def check_cis_azure_6_4(self, **kwargs):
        """
        6.4 Ensure that Network Security Group Flow Log retention period is 'greater than 90 days'
        """
        rule_section = kwargs['rule_section']

        error = get_api_error(self._network_security_groups)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._network_security_groups)
        total_resources = 0

        errors = []

        for subscription_name, response in responses.items():
            subscription_id = self.azure.get_subscription_id_by_subscription_name(subscription_name)
            if not subscription_id:
                subscription_id = subscription_name

            # 1. Get all NSG in this subscription
            all_nsg_by_id = {nsg['id'].lower(): nsg for nsg in response}

            # 2. Get all flow logs in that subscription
            total_resources += len(all_nsg_by_id)

            try:
                all_flow_logs = self.azure.network_watchers.get_all_azure_flow_logs_for_subscription(subscription_id)
            except Exception as e:
                logger.exception('Exception while getting azure flow logs')
                for nsg in all_nsg_by_id.values():
                    errors.append(
                        f'Subscription {subscription_name!r} - NSG \"{nsg.get("name") or ""}\": '
                        f'Error getting network watchers flow logs: {str(e)}')
                continue

            # 3. Go over each one
            for flow_log in all_flow_logs:
                flow_log_properties = flow_log.get('properties') or {}
                flow_log_retention_policy = flow_log_properties.get('retentionPolicy')
                flow_log_target_nsg = flow_log_properties.get('targetResourceId')

                target_nsg = all_nsg_by_id.pop(str(flow_log_target_nsg).lower(), None) or {}

                try:
                    if not flow_log_properties.get('enabled'):
                        raise ValueError(f'Flow log not enabled')
                    if not flow_log_retention_policy.get('enabled'):
                        raise ValueError(f'Retention policy not enabled')
                    if not isinstance(flow_log_retention_policy.get('days'), int) or \
                            not flow_log_retention_policy.get('days') >= 90:
                        raise ValueError(f'Retention policy is set to less than 90 days')
                except Exception as e:
                    errors.append(
                        f'Subscription {subscription_name!r} - '
                        f'NSG \"{target_nsg.get("name") or ""}\": {str(e)}'
                    )

            # 4. Go over NSG's with no flow log
            for nsg in all_nsg_by_id.values():
                errors.append(
                    f'Subscription {subscription_name!r} - '
                    f'NSG \"{nsg.get("name") or ""}\": No flow log configured'
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

    @cis_rule('6.5')
    def check_cis_azure_6_5(self, **kwargs):
        """
        6.5 Ensure that Network Watcher is 'Enabled'
        """
        rule_section = kwargs['rule_section']
        total_resources = 0
        errors = []

        for subscription_id, subscription_data in self.azure.all_subscriptions.items():
            subscription_name = subscription_data.get('displayName') or subscription_id
            try:
                all_network_watchers = self.azure.network_watchers.get_all_azure_network_watchers_for_subscription(
                    subscription_id
                )
            except Exception as e:
                self.report.add_rule_error(
                    rule_section,
                    f'Could not get network watchers ("providers/Microsoft.Network/networkWatchers"): {str(e)}'
                )
                return

            for network_watcher in all_network_watchers:
                total_resources += 1
                network_watcher_name = network_watcher.get('name') or network_watcher.get('id')
                provisioning_state = (network_watcher.get('properties') or {}).get('provisioningState')
                if str(provisioning_state).lower() != 'succeeded':
                    errors.append(
                        f'Subscription {subscription_name!r}: Network Watcher {network_watcher_name!r} is not enabled'
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
