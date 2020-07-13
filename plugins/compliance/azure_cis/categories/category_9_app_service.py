# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, bad_api_response, good_api_response, get_api_error, \
    get_api_data

logger = logging.getLogger(f'axonius.{__name__}')


def get_all_app_services(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = azure.app_service.get_all_azure_app_service_for_subscription(subscription_id)
        except Exception as e:
            logger.exception('Exception while getting app services')
            return bad_api_response(f'Error getting app services '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.Web/sites'
                                    f'?api-version=2019-08-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


class CISAzureCategory9:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()
        self._app_services = get_all_app_services(azure)

    @cis_rule('9.1')
    def check_cis_azure_9_1(self, **kwargs):
        """
        9.1 Ensure App Service Authentication is set on Azure App Service
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._app_services)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_app_services = get_api_data(self._app_services)
        total_resources = 0
        errors = []

        for subscription_name, all_app_services_in_subscription in all_app_services.items():
            for app_service in all_app_services_in_subscription:
                total_resources += 1
                app_service_name = app_service.get('name') or app_service.get('id')
                app_id = app_service['id']
                try:
                    web_config = self.azure.app_service.get_config_for_azure_app_service(app_id)
                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - '
                        f'App {app_service_name!r}: Error getting app config- {str(e)}'
                    )
                    continue
                try:
                    app_properties = web_config.get('properties') or {}

                    site_auth_enabled = app_properties.get('siteAuthEnabled')
                    if not site_auth_enabled:
                        raise ValueError(f'Site auth is not enabled')
                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - App {app_service_name!r}: {str(e)}'
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

    @cis_rule('9.2')
    def check_cis_azure_9_2(self, **kwargs):
        """
        9.2 Ensure web app redirects all HTTP traffic to HTTPS in Azure App Service
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._app_services)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_app_services = get_api_data(self._app_services)
        total_resources = 0
        errors = []

        for subscription_name, all_app_services_in_subscription in all_app_services.items():
            for app_service in all_app_services_in_subscription:
                total_resources += 1
                app_service_name = app_service.get('name') or app_service.get('id')
                try:
                    app_properties = app_service.get('properties') or {}

                    if not app_properties.get('httpsOnly'):
                        raise ValueError(f'httpsOnly is not set to \'true\'')
                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - App {app_service_name!r}: {str(e)}'
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

    @cis_rule('9.3')
    def check_cis_azure_9_3(self, **kwargs):
        """
        9.3 Ensure web app is using the latest version of TLS encryption
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._app_services)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_app_services = get_api_data(self._app_services)
        total_resources = 0
        errors = []

        for subscription_name, all_app_services_in_subscription in all_app_services.items():
            for app_service in all_app_services_in_subscription:
                total_resources += 1
                app_service_name = app_service.get('name') or app_service.get('id')
                app_id = app_service['id']
                try:
                    web_config = self.azure.app_service.get_config_for_azure_app_service(app_id)
                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - '
                        f'App {app_service_name!r}: Error getting app config- {str(e)}'
                    )
                    continue
                try:
                    app_properties = web_config.get('properties') or {}

                    min_tls_version = app_properties.get('minTlsVersion') or 'not set'
                    if min_tls_version != '1.2':
                        raise ValueError(f'minTlsVersion is {min_tls_version}')
                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - App {app_service_name!r}: {str(e)}'
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

    @cis_rule('9.4')
    def check_cis_azure_9_4(self, **kwargs):
        """
        9.4 Ensure the web app has 'Client Certificates (Incoming client certificates)' set to 'On'
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._app_services)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_app_services = get_api_data(self._app_services)
        total_resources = 0
        errors = []

        for subscription_name, all_app_services_in_subscription in all_app_services.items():
            for app_service in all_app_services_in_subscription:
                total_resources += 1
                app_service_name = app_service.get('name') or app_service.get('id')
                try:
                    app_properties = app_service.get('properties') or {}

                    if not app_properties.get('clientCertEnabled'):
                        raise ValueError(f'clientCertEnabled is not set to \'true\'')
                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - App {app_service_name!r}: {str(e)}'
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

    @cis_rule('9.5')
    def check_cis_azure_9_5(self, **kwargs):
        """
        9.5 Ensure that Register with Azure Active Directory is enabled on App Service
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._app_services)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_app_services = get_api_data(self._app_services)
        total_resources = 0
        errors = []

        for subscription_name, all_app_services_in_subscription in all_app_services.items():
            for app_service in all_app_services_in_subscription:
                total_resources += 1
                app_service_name = app_service.get('name') or app_service.get('id')
                try:
                    app_identity = app_service.get('identity') or {}

                    if not app_identity.get('principalId'):
                        raise ValueError(f'Identity is not set')
                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - App {app_service_name!r}: {str(e)}'
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
