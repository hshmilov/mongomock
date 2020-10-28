import logging

from axonius.clients.oracle_cloud.consts import ORACLE_TENANCY, ORACLE_KEY_FILE
from axonius.compliance.cis_generator import CISGeneratorBase
from compliance.oracle_cloud_cis.oracle_cloud_cis_account_report import generate_report_for_oracle_cloud_account

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=protected-access
class OracleCloudCISGenerator(CISGeneratorBase):
    def __init__(self):
        super().__init__('oracle_cloud', autoload_adapter_configs=False)
        self.all_oracle_cloud_client_configs: dict = {}
        all_configs = self._load_and_decrypt_adapter_configs()
        for config in all_configs:
            tenancy = config[ORACLE_TENANCY]
            config['key_content'] = self.plugin_base._grab_file_contents(config[ORACLE_KEY_FILE])
            self.all_oracle_cloud_client_configs[tenancy] = config

    def generate(self):
        client_config_accounts = []

        for config_id, client_config in self.all_oracle_cloud_client_configs.items():
            client_config_dict = client_config.copy()
            client_config_dict['name'] = config_id
            client_config_accounts.append(client_config_dict)

        self._generate(client_config_accounts, generate_report_for_oracle_cloud_account, 'oracle-cloud-cis')
