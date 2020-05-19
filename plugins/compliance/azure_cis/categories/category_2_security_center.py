# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, good_api_response, bad_api_response, get_api_error, \
    get_api_data

logger = logging.getLogger(f'axonius.{__name__}')


def get_security_center_builtin(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = azure.rm_subscription_get(
                'providers/Microsoft.Authorization/policyAssignments/SecurityCenterBuiltIn',
                subscription_id,
                api_version='2018-05-01'
            )
        except Exception as e:
            logger.exception('Exception while getting security center builtins')
            return bad_api_response(f'Error getting Security Center builtin policy '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.Authorization/'
                                    f'policyAssignments/SecurityCenterBuiltIn?api-version=2018-05-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


def get_security_contacts(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id
        try:
            response = list(azure.rm_subscription_paginated_get(
                'providers/Microsoft.Security/SecurityContacts',
                subscription_id,
                api_version='2017-08-01-preview'
            ))
        except Exception as e:
            logger.exception('Exception while getting security contacts')
            return bad_api_response(
                f'Error getting Security Center contacts '
                f'(/subscription/{subscription_id}/providers/Microsoft.Security/'
                f'SecurityContacts?api-version=2017-08-01-preview): '
                f'{str(e)}'
            )

        responses[subscription_name] = response

    return good_api_response(responses)


class CISAzureCategory2:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()
        self._security_center_built_in = get_security_center_builtin(azure)
        self._security_contacts = get_security_contacts(azure)

    @cis_rule('2.1')
    def check_cis_azure_2_1(self, **kwargs):
        """
        2.1 Ensure that standard pricing tier is selected
        """
        rule_section = kwargs['rule_section']
        errors = []
        total_resources = 0

        for subscription_id, subscription_data in self.azure.all_subscriptions.items():
            subscription_name = subscription_data.get('displayName') or subscription_id

            security_center_pricings = list(self.azure.rm_subscription_paginated_get(
                'providers/Microsoft.Security/pricings',
                subscription_id,
                api_version='2017-08-01-preview'
            ))
            total_resources += len(security_center_pricings)

            found_default = False

            for pricing in security_center_pricings:
                pricing_tier = pricing.get('properties', {}).get('pricingTier')
                if pricing.get('name') == 'default':
                    found_default = True
                    if pricing_tier != 'Standard':
                        errors.append(f'Found pricing tier {str(pricing_tier)} in subscription "{subscription_name}"')

            if not found_default:
                errors.append(f'Did not find any pricing tier information in subscription "{subscription_name}"')

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

    @cis_rule('2.2')
    def check_cis_azure_2_2(self, **kwargs):
        """
        2.2 Ensure that 'Automatic provisioning of monitoring agent' is set to 'On'
        """
        rule_section = kwargs['rule_section']
        errors = []
        total_resources = 0

        for subscription_id, subscription_data in self.azure.all_subscriptions.items():
            subscription_name = subscription_data.get('displayName') or subscription_id

            auto_provision_settings = list(self.azure.rm_subscription_paginated_get(
                'providers/Microsoft.Security/autoProvisioningSettings',
                subscription_id,
                api_version='2017-08-01-preview'
            ))

            total_resources += len(auto_provision_settings)

            found_default = False

            for auto_provision in auto_provision_settings:
                auto_provision_value = str(auto_provision.get('properties', {}).get('autoProvision'))
                if auto_provision.get('name') == 'default':
                    found_default = True
                    if str(auto_provision_value).lower() != 'on':
                        errors.append(
                            f'Subscription "{subscription_name}": Automatic provisioning of '
                            f'monitoring agent is set to "{str(auto_provision_value)}"')

            if not found_default:
                errors.append(f'Subscription "{subscription_name}": Did not find any '
                              f'automatic provisioning of monitoring agent settings')

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

    def check_security_center_builtin_rule(self, rule_section: str, param: str):
        errors = []
        error = get_api_error(self._security_center_built_in)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._security_center_built_in)
        total_resources = len(responses.keys())

        for subscription_name, response in responses.items():
            if not isinstance(response, dict) or not response.get('properties'):
                errors.append(
                    f'Subscription "{subscription_name}": Invalid response: {str(response)}'
                )
                continue

            if response.get('name') != 'SecurityCenterBuiltIn':
                errors.append(
                    f'Subscription "{subscription_name}": Could not find "SecurityCenterBuiltIn" ASC Default settings. '
                    f'Got instead: "{str(response.get("name"))}"'
                )
                continue

            if response.get('properties', {}).get('parameters', {}).get(param, {}).get('value') == 'Disabled':
                errors.append(
                    f'Subscription "{subscription_name}": The "{param}" value is set to Disabled.'
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

    @cis_rule('2.3')
    def check_cis_azure_2_3(self, **kwargs):
        """
        2.3 Ensure ASC Default policy setting "Monitor System Updates" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'systemUpdatesMonitoringEffect')

    @cis_rule('2.4')
    def check_cis_azure_2_4(self, **kwargs):
        """
        2.4 Ensure ASC Default policy setting "Monitor OS Vulnerabilities" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'systemConfigurationsMonitoringEffect')

    @cis_rule('2.5')
    def check_cis_azure_2_5(self, **kwargs):
        """
        2.5 Ensure ASC Default policy setting "Monitor Endpoint Protection" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'endpointProtectionMonitoringEffect')

    @cis_rule('2.6')
    def check_cis_azure_2_6(self, **kwargs):
        """
        2.6 Ensure ASC Default policy setting "Monitor Disk Encryption" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'diskEncryptionMonitoringEffect')

    @cis_rule('2.7')
    def check_cis_azure_2_7(self, **kwargs):
        """
        2.7 Ensure ASC Default policy setting "Monitor Network Security Groups" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'networkSecurityGroupsMonitoringEffect')

    @cis_rule('2.8')
    def check_cis_azure_2_8(self, **kwargs):
        """
        2.8 Ensure ASC Default policy setting "Monitor Web Application Firewall" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'webApplicationFirewallMonitoringEffect')

    @cis_rule('2.9')
    def check_cis_azure_2_9(self, **kwargs):
        """
        2.9 Ensure ASC Default policy setting "Enable Next Generation Firewall(NGFW) Monitoring" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'nextGenerationFirewallMonitoringEffect')

    @cis_rule('2.10')
    def check_cis_azure_2_10(self, **kwargs):
        """
        2.10 Ensure ASC Default policy setting "Monitor Vulnerability Assessment" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'vulnerabilityAssesmentMonitoringEffect')

    @cis_rule('2.11')
    def check_cis_azure_2_11(self, **kwargs):
        """
        2.11 Ensure ASC Default policy setting "Monitor Storage Blob Encryption" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'storageEncryptionMonitoringEffect')

    @cis_rule('2.12')
    def check_cis_azure_2_12(self, **kwargs):
        """
        2.12 Ensure ASC Default policy setting "Monitor JIT Network Access" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'jitNetworkAccessMonitoringEffect')

    @cis_rule('2.13')
    def check_cis_azure_2_13(self, **kwargs):
        """
        2.13 Ensure ASC Default policy setting "Monitor Adaptive Application Whitelisting" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'adaptiveApplicationControlsMonitoringEffect')

    @cis_rule('2.14')
    def check_cis_azure_2_14(self, **kwargs):
        """
        2.14 Ensure ASC Default policy setting "Monitor SQL Auditing" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'sqlAuditingMonitoringEffect')

    @cis_rule('2.15')
    def check_cis_azure_2_15(self, **kwargs):
        """
        2.15 Ensure ASC Default policy setting "Monitor SQL Encryption" is not "Disabled"
        """
        self.check_security_center_builtin_rule(kwargs['rule_section'], 'sqlEncryptionMonitoringEffect')

    @cis_rule('2.16')
    def check_cis_azure_2_16(self, **kwargs):
        """
        2.16 Ensure that 'Security contact emails' is set
        """
        rule_section = kwargs['rule_section']
        errors = []

        error = get_api_error(self._security_contacts)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._security_contacts)
        total_resources = len(responses.keys())

        for subscription_name, response in responses.items():
            email = None
            for policy in response:
                if policy.get('name') == 'default1':
                    email = policy.get('properties', {}).get('email')

            if not email:
                errors.append(
                    f'Subscription "{subscription_name}": Could not find security contact mail'
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

    @cis_rule('2.17')
    def check_cis_azure_2_17(self, **kwargs):
        """
        2.17 Ensure that security contact 'Phone number' is set
        """
        rule_section = kwargs['rule_section']
        errors = []

        error = get_api_error(self._security_contacts)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._security_contacts)
        total_resources = len(responses.keys())

        for subscription_name, response in responses.items():
            phone = None
            for policy in response:
                if policy.get('name') == 'default1':
                    phone = policy.get('properties', {}).get('phone')

            if not phone:
                errors.append(
                    f'Subscription "{subscription_name}": Could not find security contact phone'
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

    @cis_rule('2.18')
    def check_cis_azure_2_18(self, **kwargs):
        """
        2.18 Ensure that 'Send email notification for high severity alerts' is set to 'On'
        """
        rule_section = kwargs['rule_section']
        errors = []

        error = get_api_error(self._security_contacts)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._security_contacts)
        total_resources = len(responses.keys())

        for subscription_name, response in responses.items():
            alert_notifications = None
            for policy in response:
                if policy.get('name') == 'default1':
                    alert_notifications = policy.get('properties', {}).get('alertNotifications')

            if str(alert_notifications).lower() != 'on':
                errors.append(f'Subscription "{subscription_name}": "Send email notification for '
                              f'high severity alerts" is set to Off')
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

    @cis_rule('2.19')
    def check_cis_azure_2_19(self, **kwargs):
        """
        2.19 Ensure that 'Send email also to subscription owners' is set to 'On'
        """
        rule_section = kwargs['rule_section']
        errors = []

        error = get_api_error(self._security_contacts)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        responses = get_api_data(self._security_contacts)
        total_resources = len(responses.keys())

        for subscription_name, response in responses.items():
            alert_to_admins = None
            for policy in response:
                if policy.get('name') == 'default1':
                    alert_to_admins = policy.get('properties', {}).get('alertsToAdmins')

            if str(alert_to_admins).lower() != 'on':
                errors.append(
                    f'Subscription "{subscription_name}": '
                    f'"Send email notification to subscription owners" is set to Off'
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
