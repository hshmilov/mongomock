import datetime
import logging
import concurrent.futures
import time

from typing import List

from axonius.consts.plugin_consts import COMPLIANCE_PLUGIN_NAME
from axonius.plugin_base import PluginBase
from compliance.aws_cis.aws_cis_account_report import generate_report_for_aws_account

logger = logging.getLogger(f'axonius.{__name__}')


NUMBER_OF_PARALLEL_PROCESSES = 5
TIMEOUT_FOR_RESULT_GENERATION = 60 * 60 * 5     # 5 hours


# pylint: disable=protected-access
class AWSCISGenerator:
    def __init__(self):
        self.plugin_base: PluginBase = PluginBase.Instance
        self.all_aws_client_configs: List[dict] = []

        for aws_plugin_config in self.plugin_base.core_configs_collection.find({'plugin_name': 'aws_adapter'}):
            aws_plugin_unique_name = aws_plugin_config.get('plugin_unique_name')
            if not aws_plugin_unique_name:
                continue
            try:
                for aws_client in self.plugin_base._get_db_connection()[aws_plugin_unique_name]['clients'].find({}):
                    aws_client_config = aws_client['client_config'].copy()
                    self.plugin_base._decrypt_client_config(aws_client_config)
                    aws_client_config['plugin_unique_name'] = aws_plugin_unique_name
                    self.all_aws_client_configs.append(aws_client_config)
            except Exception:
                logger.exception(f'Could not add client config of {aws_plugin_unique_name}')

    def generate(self):
        # We need to iterate through all different accounts to make one aggregated cis report.
        # 1. Go iterate through each aws connection
        #    a. For each aws connection, iterate through the aws iam itself, and all assumed roles. each one is a
        #       set of credentials.
        #       i. for each set of credentials, send it to a report generator. The report generator will decide
        #          which regions or services it would like to use.
        for aws_client_config in self.all_aws_client_configs:
            # Prepare all accounts creds
            client_config_id = '_'.join([
                aws_client_config.get('account_tag', ''),
                aws_client_config.get('aws_access_key_id', 'attached-profile'),
                aws_client_config.get('region_name', 'ALL')
            ])
            logger.info(f'Parsing client_config {client_config_id}')
            client_config_template = {
                'aws_access_key_id': aws_client_config.get('aws_access_key_id'),
                'aws_secret_access_key': aws_client_config.get('aws_secret_access_key'),
                'region_name': aws_client_config.get('region_name'),
                'https_proxy': aws_client_config.get('proxy'),
                'get_all_regions': aws_client_config.get('get_all_regions'),
                'use_attached_iam_role': aws_client_config.get('use_attached_iam_role')
            }

            client_config_accounts = []
            iam_client_config = client_config_template.copy()
            iam_client_config['name'] = 'iam_' + client_config_id
            iam_client_config['type'] = 'iam'
            client_config_accounts.append(iam_client_config)

            if aws_client_config.get('roles_to_assume_list'):
                roles_to_assume_file = self.plugin_base._grab_file_contents(
                    aws_client_config.get('roles_to_assume_list'),
                    alternative_db_name=aws_client_config['plugin_unique_name']
                ).decode('utf-8')

                for role_arn in roles_to_assume_file.strip().split(','):
                    role_client_config = client_config_template.copy()
                    role_client_config['name'] = role_arn.strip() + '_' + client_config_id
                    role_client_config['assumed_role_arn'] = role_arn.strip()
                    role_client_config['type'] = 'role'
                    client_config_accounts.append(role_client_config)

            # client_config_accounts is all of the different connections to different accounts we have. We can
            # start sending them to the different functions

            with concurrent.futures.ProcessPoolExecutor(max_workers=NUMBER_OF_PARALLEL_PROCESSES) as executor:
                logger.info(f'Generating reports for {len(client_config_accounts)} accounts '
                            f'with a pool of {NUMBER_OF_PARALLEL_PROCESSES} processes')
                futures_to_data = {
                    executor.submit(generate_report_for_aws_account, client_config_account): (time.time())
                    for client_config_account in client_config_accounts
                }
                for future in concurrent.futures.as_completed(futures_to_data, timeout=TIMEOUT_FOR_RESULT_GENERATION):
                    start_time = futures_to_data[future]
                    try:
                        account_id, account_name, report_json = future.result()

                        rules = report_json.get('rules', [])
                        if not report_json or len(rules) == 0:
                            logger.error(f'Report finished empty for "{account_name}" ({account_id}')
                            continue

                        PluginBase.Instance._get_db_connection()[COMPLIANCE_PLUGIN_NAME]['reports'].insert_one(
                            {
                                'account_id': account_id,
                                'account_name': account_name,
                                'report': report_json,
                                'type': 'aws-cis',
                                'last_updated': datetime.datetime.now()
                            }
                        )

                        logger.info(f'Finished AWS-CIS report for "{account_name}" ({account_id} '
                                    f'in {time.time() - start_time} seconds.')
                    except Exception:
                        logger.exception(f'Could not get results in cloud-compliance')

            logger.info(f'Done parsing client_config {client_config_id}')
