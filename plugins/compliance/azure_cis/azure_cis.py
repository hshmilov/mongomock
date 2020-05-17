import datetime
import logging
import concurrent.futures
import time

from axonius.clients.azure.consts import AZURE_TENANT_ID, AZURE_ACCOUNT_TAG
from axonius.consts.plugin_consts import COMPLIANCE_PLUGIN_NAME
from axonius.plugin_base import PluginBase
from compliance.azure_cis.azure_cis_account_report import generate_report_for_azure_account

logger = logging.getLogger(f'axonius.{__name__}')


NUMBER_OF_PARALLEL_PROCESSES = 5
TIMEOUT_FOR_RESULT_GENERATION = 60 * 60 * 5     # 5 hours


# pylint: disable=protected-access
class AzureCISGenerator:
    def __init__(self):
        self.plugin_base: PluginBase = PluginBase.Instance
        self.all_azure_client_configs: dict = {}

        db_connection = self.plugin_base._get_db_connection()

        for azure_client_config in self.plugin_base.core_configs_collection.find({'plugin_name': 'azure_adapter'}):
            azure_plugin_unique_name = azure_client_config.get('plugin_unique_name')
            if not azure_plugin_unique_name:
                continue
            try:
                for azure_client in db_connection[azure_plugin_unique_name]['clients'].find({}):
                    azure_client_config = azure_client['client_config'].copy()
                    self.plugin_base._decrypt_client_config(azure_client_config)

                    azure_client_config['plugin_unique_name'] = azure_plugin_unique_name
                    azure_client_config['azure_adapter_type'] = 'azure'

                    tenant_id = azure_client_config[AZURE_TENANT_ID]

                    self.all_azure_client_configs[tenant_id] = azure_client_config
            except Exception:
                logger.exception(f'Could not add client config of {azure_plugin_unique_name}')

        for azure_ad_client_config in self.plugin_base.core_configs_collection.find(
                {'plugin_name': 'azure_ad_adapter'}
        ):
            azure_ad_plugin_unique_name = azure_ad_client_config.get('plugin_unique_name')
            if not azure_ad_plugin_unique_name:
                continue
            try:
                for azure_client in db_connection[azure_ad_plugin_unique_name]['clients'].find({}):
                    azure_ad_client_config = azure_client['client_config'].copy()
                    self.plugin_base._decrypt_client_config(azure_ad_client_config)

                    azure_ad_client_config['plugin_unique_name'] = azure_ad_plugin_unique_name
                    azure_ad_client_config['azure_adapter_type'] = 'azure_ad'

                    tenant_id = azure_ad_client_config[AZURE_TENANT_ID]
                    if tenant_id not in self.all_azure_client_configs:
                        # Note! we do not add duplicate values here. In fact - this means we prioritize
                        # azure over azure ad. The reason for that is that usually azure just contains
                        # far more information than azure ad.
                        # However, there are bad things here as well - Azure AD is capable of
                        # having intune authentication code + b2c checkbox information. We currently assume two things:
                        # - there is no use of intune authentication code in CIS and so this is irrelevant
                        # - Azure AD B2C can not be put into a regular azure adapter as it is not a compute capable
                        #   account, and thus we will not miss any b2c information since it will be exclusive
                        #   to the azure ad adapter.
                        self.all_azure_client_configs[tenant_id] = azure_ad_client_config
            except Exception:
                logger.exception(f'Could not add client config of {azure_ad_plugin_unique_name}')

    def generate(self):
        # We need to iterate through all different accounts to make one aggregated cis report.
        # 1. Go iterate through each Azure connection
        #    - In the future, add support of 'get all subscriptions'

        client_config_accounts = []

        for azure_client_config in self.all_azure_client_configs:
            # Prepare all accounts creds
            client_config_id = '_'.join([
                azure_client_config.get(AZURE_ACCOUNT_TAG, ''),
                azure_client_config.get(AZURE_TENANT_ID, 'unknown-tenant-id')
            ])

            logger.info(f'Parsing client_config {client_config_id}')

            azure_client_config_dict = azure_client_config.copy()
            azure_client_config_dict['name'] = client_config_id
            client_config_accounts.append(azure_client_config_dict)

        # Run the different reports for the accounts here
        with concurrent.futures.ProcessPoolExecutor(max_workers=NUMBER_OF_PARALLEL_PROCESSES) as executor:
            logger.info(f'Generating reports for {len(client_config_accounts)} accounts '
                        f'with a pool of {NUMBER_OF_PARALLEL_PROCESSES} processes')

            futures_to_data = {
                executor.submit(generate_report_for_azure_account, client_config_account): (time.time())
                for client_config_account in client_config_accounts
            }

            for future in concurrent.futures.as_completed(futures_to_data, timeout=TIMEOUT_FOR_RESULT_GENERATION):
                start_time = futures_to_data[future]
                try:
                    account_id, account_name, report_json = future.result()
                    PluginBase.Instance._get_db_connection()[COMPLIANCE_PLUGIN_NAME]['reports'].insert_one(
                        {
                            'account_id': account_id,
                            'account_name': account_name,
                            'report': report_json,
                            'last_updated': datetime.datetime.now()
                        }
                    )
                except Exception:
                    logger.exception(f'Could not get results in cloud-compliance')

                logger.info(f'Finished Azure-CIS report for "{account_name}" ({account_id} '
                            f'in {time.time() - start_time} seconds.')
