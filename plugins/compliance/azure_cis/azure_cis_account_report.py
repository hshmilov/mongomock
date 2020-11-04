"""
Generates an Azure CIS report per one account
"""
import logging
from typing import Tuple

from axonius.clients.azure.client import AzureCloudConnection
from axonius.clients.azure.consts import AZURE_TENANT_ID, AZURE_ACCOUNT_TAG, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, \
    AZURE_CLOUD_ENVIRONMENT, AZURE_AD_CLOUD_ENVIRONMENT, AzureClouds, AZURE_STACK_HUB_URL, \
    AZURE_STACK_HUB_RESOURCE, AZURE_STACK_HUB_PROXY_SETTINGS, AZURE_HTTPS_PROXY, AZURE_VERIFY_SSL, AZURE_IS_AZURE_AD_B2C
from compliance.azure_cis.azure_cis_rules import generate_rules, generate_failed_report
from compliance.utils.AzureAccountReport import AzureAccountReport

logger = logging.getLogger(f'axonius.{__name__}')


def get_session_by_account_dict(account_dict: dict) -> AzureCloudConnection:
    account_type = account_dict.get('azure_adapter_type')
    if account_type == 'azure':
        cloud_key = AZURE_CLOUD_ENVIRONMENT
    elif account_type == 'azure_ad':
        # 'azure_ad' currently not implemented. maybe will be in the future.
        cloud_key = AZURE_AD_CLOUD_ENVIRONMENT
    else:
        raise ValueError(f'Unknown Azure Adapter type {account_type}!')

    cloud = {
        'Global': AzureClouds.Public,
        'China': AzureClouds.China,
        'Azure Public Cloud': AzureClouds.Public,
        'Azure China Cloud': AzureClouds.China,
        'Azure German Cloud': AzureClouds.Germany,
        'Azure US Gov Cloud': AzureClouds.Gov
    }.get(account_dict.get(cloud_key))

    management_url = None
    resource = None
    azure_stack_hub_proxy_settings = None

    if account_dict.get(AZURE_STACK_HUB_URL) and account_dict.get(AZURE_STACK_HUB_RESOURCE):
        logger.info(f'Initializing Azure Stack Hub Azure-CIS report')
        management_url = account_dict[AZURE_STACK_HUB_URL]
        resource = account_dict[AZURE_STACK_HUB_RESOURCE]
        azure_stack_hub_proxy_settings = account_dict.get(AZURE_STACK_HUB_PROXY_SETTINGS)

    with AzureCloudConnection(
            app_client_id=account_dict[AZURE_CLIENT_ID],
            app_client_secret=account_dict[AZURE_CLIENT_SECRET],
            tenant_id=account_dict[AZURE_TENANT_ID],
            cloud=cloud,
            management_url=management_url,
            resource=resource,
            azure_stack_hub_proxy_settings=azure_stack_hub_proxy_settings,
            is_azure_ad_b2c=account_dict.get(AZURE_IS_AZURE_AD_B2C),
            https_proxy=account_dict.get(AZURE_HTTPS_PROXY),
            verify_ssl=account_dict.get(AZURE_VERIFY_SSL)
    ) as connection:
        return connection


def generate_report_for_azure_account(account_dict: dict) -> Tuple[str, str, dict]:
    account_name = account_dict.get('name') or 'unknown'
    logger.info(f'Parsing account {account_name}')
    report = AzureAccountReport()

    account_id = account_dict[AZURE_TENANT_ID]
    account_name = account_id
    account_tag = account_dict.get(AZURE_ACCOUNT_TAG)

    if account_tag:
        account_name = f'{account_tag} ({account_id})'

    try:
        azure_client = get_session_by_account_dict(account_dict)
    except Exception as e:
        logger.exception(f'Exception while generating Azure report for {account_name} - could not get initial session')
        generate_failed_report(report, f'Could not generate azure connection: {str(e)}')
        return account_id.strip(), account_name.strip(), report.get_json()

    try:
        # Get tenant name / account alias
        with azure_client:
            org_info = azure_client.get_organization_information()
            account_id = org_info['id']
            account_alias = org_info['displayName']
    except Exception:
        logger.exception(f'Could not get account alias for {account_name}')
        account_alias = None

    if account_alias and account_tag:
        account_name = f'{account_alias} ({account_tag} - {account_id})'
    elif account_alias:
        account_name = f'{account_alias} ({account_id})'

    try:
        generate_rules(report, azure_client, account_dict)
    except Exception:
        logger.exception(f'Exception while generating rules for Azure account {account_name}')
    return account_id.strip(), account_name.strip(), report.get_json()
