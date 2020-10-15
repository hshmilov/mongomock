import json
import sys

import pymongo

from axonius.clients.azure.consts import AZURE_ACCOUNT_TAG, AZURE_TENANT_ID
from axonius.plugin_base import PluginBase
from compliance.azure_cis.azure_cis_account_report import generate_report_for_azure_account
from testing.test_credentials.test_azure_credentials import client_details as azure_client_config


class PluginBaseMock:
    def __init__(self):
        self._configured_session_timeout = (5, 300)

    @staticmethod
    def _get_db_connection():
        return pymongo.MongoClient('mongo.axonius.local:27017', username='ax_user', password='ax_pass',
                                   connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)


def init_env():
    PluginBase.Instance = PluginBaseMock()


def main():
    print(f'Starting')
    init_env()

    try:
        rules_starts_with_filter = sys.argv[1]
    except Exception:
        rules_starts_with_filter = None

    account_dict = azure_client_config.copy()
    account_dict['azure_adapter_type'] = 'azure'
    account_dict['plugin_unique_name'] = 'azure_adapter_0'
    account_dict['name'] = '_'.join([
        azure_client_config.get(AZURE_ACCOUNT_TAG) or '',
        azure_client_config.get(AZURE_TENANT_ID) or 'unknown-tenant-id'
    ])

    account_id, account_name, report = generate_report_for_azure_account(account_dict)
    print(f'Account ID: {account_id}')
    print(f'Account Name: {account_name}')
    print(f' ')
    if rules_starts_with_filter:
        for rule in report['rules']:
            if rule['section'].startswith(rules_starts_with_filter):
                print(json.dumps(rule, indent=4))
    else:
        print(json.dumps(report, indent=4))


if __name__ == '__main__':
    sys.exit(main())
