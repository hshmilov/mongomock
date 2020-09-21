import datetime
import logging
import concurrent.futures
import time

from axonius.clients.azure.consts import AZURE_TENANT_ID, AZURE_ACCOUNT_TAG, AZURE_SUBSCRIPTION_ID
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

                    # Subscriptions is not interesting here. we will later understand automatically what we
                    # have access to.
                    azure_client_config.pop(AZURE_SUBSCRIPTION_ID, None)

                    tenant_id = azure_client_config[AZURE_TENANT_ID]
                    if tenant_id not in self.all_azure_client_configs:
                        self.all_azure_client_configs[tenant_id] = azure_client_config
            except Exception:
                logger.exception(f'Could not add client config of {azure_plugin_unique_name}')

        # Note that we are not looking at azure-ad at all.

    def generate(self):
        # We need to iterate through all different accounts to make one aggregated cis report.
        # 1. Go iterate through each Azure connection
        #    - In the future, add support of 'get all subscriptions'

        client_config_accounts = []

        for azure_client_config in self.all_azure_client_configs.values():
            # Prepare all accounts creds
            client_config_id = '_'.join([
                azure_client_config.get(AZURE_ACCOUNT_TAG) or '',
                azure_client_config.get(AZURE_TENANT_ID) or 'unknown-tenant-id'
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
                    PluginBase.Instance._get_db_connection()[COMPLIANCE_PLUGIN_NAME]['azure_reports'].insert_one(
                        {
                            'account_id': account_id,
                            'account_name': account_name,
                            'report': report_json,
                            'type': 'azure-cis',
                            'last_updated': datetime.datetime.now()
                        }
                    )

                    logger.info(f'Finished Azure-CIS report for "{account_name}" ({account_id} '
                                f'in {time.time() - start_time} seconds.')
                except Exception:
                    logger.exception(f'Could not get results in cloud-compliance')
