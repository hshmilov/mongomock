import datetime
import logging
import concurrent.futures
import time

from typing import Union, Callable, Tuple, List
from axonius.consts.compliance_consts import NUMBER_OF_PARALLEL_PROCESSES, TIMEOUT_FOR_RESULT_GENERATION, \
    COMPLIANCE_REPORTS_COLLECTIONS
from axonius.consts.plugin_consts import COMPLIANCE_PLUGIN_NAME
from axonius.plugin_base import PluginBase

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=protected-access
class CISGeneratorBase:
    def __init__(self,
                 module_name: str,
                 adapter_name: str = '',
                 autoload_adapter_configs: bool = False,
                 ):
        """
        Base CIS Report Generator.
        If autoload_adapter_configs is True, then self._adapter_client_configs will
        be populated with client configs that match the supplied adapter plugin name
        :param module_name: Name of the module, see compliance_consts.COMPLIANCE_MODULES
        :param adapter_name: Specify a different adapter name. If empty, the module_name will be used.
        :param autoload_adapter_configs: whether or not to automatically load and decrypt client configs
        """
        self.module_name = module_name
        self.plugin_base: PluginBase = PluginBase.Instance
        self._adapter_client_configs: dict = {}  # Protected because configs are not encrypted!
        self.adapter_name = self._get_valid_adapter_name(adapter_name or module_name)
        if not self.adapter_name:
            logger.debug(f'Adapter name for cis generator invalid or not specified. got: {self.adapter_name}')

        if self.adapter_name and autoload_adapter_configs:
            self._adapter_client_configs = self._load_and_decrypt_adapter_configs()

    @staticmethod
    def _get_valid_adapter_name(adapter_name: str) -> Union[str, None]:
        """
        Make sure the supplied adapter name ends with `_adapter`
        :param adapter_name: adapter to sanitize
        :type adapter_name: str
        :return: adapter name sanitized (e.g. aws_adapter) or None if adapter_name is not valid
        :rtype: str or None
        """
        if not adapter_name:
            return None
        if adapter_name and not isinstance(adapter_name, str):
            adapter_name = str(adapter_name)
        try:
            if adapter_name.endswith('_adapter'):
                return adapter_name
            return f'{adapter_name}_adapter'
        except Exception:
            logger.exception(f'Bad adapter name: {adapter_name}')
            return str(adapter_name)

    def _load_and_decrypt_adapter_configs(self, adapter_name: str = '') -> List[dict]:
        """
        Load and decrypt adapter configs for `adapter_name` or for `self.adapter_name`
        :param adapter_name: Adapter plugin_name to load all client configs for. Use `self.adapter_name` if left empty.
        :type adapter_name: str
        :return: list containing decrypted client configs for the adapter
        :rtype: list
        """
        adapter_name_clean = self._get_valid_adapter_name(adapter_name) or self.adapter_name
        if not adapter_name_clean:
            return []

        db_connection = self.plugin_base._get_db_connection()
        client_configs = []
        for client_config in self.plugin_base.core_configs_collection.find(
                {'plugin_name': adapter_name_clean}):
            plugin_unique_name = client_config.get('plugin_unique_name')
            if not plugin_unique_name:
                continue
            try:
                for client in db_connection[plugin_unique_name]['clients'].find({}):
                    client_config = client['client_config'].copy()
                    self.plugin_base._decrypt_client_config(client_config)

                    client_config['plugin_unique_name'] = plugin_unique_name
                client_configs.append(client_config)
            except Exception:
                logger.exception(f'Could not add client config of {plugin_unique_name}')
        return client_configs

    def generate(self):
        """
        Generate a report. This needs to be implemented by the subclass.
        """
        raise NotImplementedError()

    def _generate(self,
                  accounts: List[dict],
                  account_report_factory: Callable[[dict], Tuple[str, str, dict]],
                  report_type: str):
        """
        Generate a report using concurrent.futures ProcesPoolExecutor for the list of accounts, into this module's
        report collection
        :param accounts: List of accounts to run on
        :param account_report_factory: Method to execute for each account
            example: azure_cis_account_report.generate_report_for_azure_account
        :param report_type: str type of the report (example: 'azure-cis')
        """
        # Run the different reports for the accounts here
        report_collection = COMPLIANCE_REPORTS_COLLECTIONS[self.module_name]
        with concurrent.futures.ProcessPoolExecutor(max_workers=NUMBER_OF_PARALLEL_PROCESSES) as executor:
            logger.info(f'Generating reports for {len(accounts)} accounts '
                        f'with a pool of {NUMBER_OF_PARALLEL_PROCESSES} processes')

            futures_to_data = {
                executor.submit(account_report_factory, client_config_account): (time.time())
                for client_config_account in accounts
            }

            for future in concurrent.futures.as_completed(futures_to_data, timeout=TIMEOUT_FOR_RESULT_GENERATION):
                start_time = futures_to_data[future]
                try:
                    account_id, account_name, report_json = future.result()
                    PluginBase.Instance._get_db_connection()[COMPLIANCE_PLUGIN_NAME][report_collection].insert_one(
                        {
                            'account_id': account_id,
                            'account_name': account_name,
                            'report': report_json,
                            'type': report_type,
                            'last_updated': datetime.datetime.now()
                        }
                    )

                    logger.info(f'Finished {report_type} report for "{account_name}" ({account_id} '
                                f'in {time.time() - start_time} seconds.')
                except Exception:
                    logger.exception(f'Could not get results in cloud-compliance')
