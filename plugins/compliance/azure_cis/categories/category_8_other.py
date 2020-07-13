# pylint: disable=too-many-branches, too-many-nested-blocks
import logging

from axonius.clients.azure.client import AzureCloudConnection
from compliance.utils.AzureAccountReport import AzureAccountReport
from compliance.utils.account_report import RuleStatus
from compliance.utils.cis_utils import cis_rule, errors_to_gui, bad_api_response, good_api_response, get_api_error, \
    get_api_data

logger = logging.getLogger(f'axonius.{__name__}')


def get_all_keyvaults(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = azure.keyvault.get_all_azure_keyvaults_for_subscription(subscription_id)
        except Exception as e:
            logger.exception('Exception while getting key vaults')
            return bad_api_response(f'Error getting key vaults '
                                    f'(/subscription/{subscription_id}/providers/Microsoft.KeyVault/vaults'
                                    f'?api-version=2019-09-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


def get_all_kubernetes_clusters(azure: AzureCloudConnection):
    responses = {}
    for subscription_id, subscription_data in azure.all_subscriptions.items():
        subscription_name = subscription_data.get('displayName') or subscription_id

        try:
            response = azure.kubernetes.get_all_azure_kubernetes_for_subscription(subscription_id)
        except Exception as e:
            logger.exception('Exception while getting kubernetes clusters')
            return bad_api_response(f'Error getting kubernetes clusters '
                                    f'(/subscription/{subscription_id}/providers/'
                                    f'Microsoft.ContainerService/managedClusters'
                                    f'?api-version=2020-04-01): '
                                    f'{str(e)}')

        responses[subscription_name] = response

    return good_api_response(responses)


class CISAzureCategory8:
    def __init__(self, report: AzureAccountReport, azure: AzureCloudConnection, account_dict: dict):
        self.report = report
        self.azure = azure
        self._account_dict = account_dict.copy()
        self._key_vaults = get_all_keyvaults(azure)
        self._kubernetes_clustesrs = get_all_kubernetes_clusters(azure)

    @cis_rule('8.1')
    def check_cis_azure_8_1(self, **kwargs):
        """
        8.1 Ensure that the expiration date is set on all keys
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._key_vaults)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_key_vaults = get_api_data(self._key_vaults)
        total_resources = 0
        errors = []

        for subscription_name, all_keyvaults_in_subscription in all_key_vaults.items():
            for vault in all_keyvaults_in_subscription:
                vault_name = vault.get('name') or vault.get('id')
                vault_uri = (vault.get('properties') or {}).get('vaultUri')
                if not vault_uri:
                    continue
                try:
                    keys = self.azure.keyvault.get_all_keys_for_vault(vault_uri)
                except Exception as e:
                    total_resources += 1
                    errors.append(
                        f'Subscription "{subscription_name}" - Vault {vault_name!r}: '
                        f'Can not get keys. Error: {str(e)}'
                    )
                    continue

                for key in keys:
                    total_resources += 1
                    try:
                        key_attributes = key.get('attributes') or {}
                        if key_attributes.get('enabled') and not key_attributes.get('exp'):
                            raise ValueError(f'Key {key["id"]!r} does not have expiration date')
                    except Exception as e:
                        errors.append(
                            f'Subscription "{subscription_name}" - Vault {vault_name!r}: {str(e)}'
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

    @cis_rule('8.2')
    def check_cis_azure_8_2(self, **kwargs):
        """
        8.2 Ensure that the expiration date is set on all Secrets
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._key_vaults)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_key_vaults = get_api_data(self._key_vaults)
        total_resources = 0
        errors = []

        for subscription_name, all_keyvaults_in_subscription in all_key_vaults.items():
            for vault in all_keyvaults_in_subscription:
                vault_name = vault.get('name') or vault.get('id')
                vault_uri = (vault.get('properties') or {}).get('vaultUri')
                if not vault_uri:
                    continue
                try:
                    secrets = self.azure.keyvault.get_all_secrets_for_vault(vault_uri)
                except Exception as e:
                    total_resources += 1
                    errors.append(
                        f'Subscription "{subscription_name}" - Vault {vault_name!r}: '
                        f'Can not get secrets. Error: {str(e)}'
                    )
                    continue

                for secret in secrets:
                    total_resources += 1
                    try:
                        secret_attributes = secret.get('attributes') or {}
                        if secret_attributes.get('enabled') and not secret_attributes.get('exp'):
                            raise ValueError(f'Secret {secret["id"]!r} does not have expiration date')
                    except Exception as e:
                        errors.append(
                            f'Subscription "{subscription_name}" - Vault {vault_name!r}: {str(e)}'
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

    @cis_rule('8.4')
    def check_cis_azure_8_4(self, **kwargs):
        """
        8.4 Ensure the key vault is recoverable
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._key_vaults)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_key_vaults = get_api_data(self._key_vaults)
        total_resources = 0
        errors = []

        for subscription_name, all_keyvaults_in_subscription in all_key_vaults.items():
            for vault in all_keyvaults_in_subscription:
                total_resources += 1
                vault_name = vault.get('name') or vault.get('id')
                try:
                    vault_properties = vault.get('properties') or {}

                    if not vault_properties.get('enableSoftDelete'):
                        raise ValueError(f'enableSoftDelete not enabled')
                    if not vault_properties.get('enablePurgeProtection'):
                        raise ValueError(f'enablePurgeProtection not enabled')
                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - Vault {vault_name!r}: {str(e)}'
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

    @cis_rule('8.5')
    def check_cis_azure_8_5(self, **kwargs):
        """
        8.5 Enable role-based access control (RBAC) within Azure Kubernetes Services
        """
        rule_section = kwargs['rule_section']
        error = get_api_error(self._kubernetes_clustesrs)
        if error:
            self.report.add_rule_error(rule_section, error)
            return

        all_kubernetes_clusters = get_api_data(self._kubernetes_clustesrs)
        total_resources = 0
        errors = []

        for subscription_name, all_kubernetes_in_subscription in all_kubernetes_clusters.items():
            for kubernetes in all_kubernetes_in_subscription:
                total_resources += 1
                cluster_name = kubernetes.get('name') or kubernetes.get('id')
                try:
                    cluster_properties = kubernetes.get('properties') or {}

                    if not cluster_properties.get('enableRBAC'):
                        raise ValueError(f'RBAC not enabled')
                except Exception as e:
                    errors.append(
                        f'Subscription "{subscription_name}" - Cluster {cluster_name!r}: {str(e)}'
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
