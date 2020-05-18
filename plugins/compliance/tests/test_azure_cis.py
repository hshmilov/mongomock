import json
import sys

from axonius.clients.azure.consts import AZURE_ACCOUNT_TAG, AZURE_TENANT_ID
from compliance.azure_cis.azure_cis_account_report import generate_report_for_azure_account
from testing.test_credentials.test_azure_credentials import client_details as azure_client_config


def main():
    print(f'Starting')

    try:
        rules_starts_with_filter = sys.argv[1]
    except Exception:
        rules_starts_with_filter = None

    account_dict = azure_client_config.copy()
    account_dict['azure_adapter_type'] = 'azure'
    account_dict['plugin_unique_name'] = 'azure_adapter_0'
    account_dict['name'] = '_'.join([
        azure_client_config.get(AZURE_ACCOUNT_TAG, ''),
        azure_client_config.get(AZURE_TENANT_ID, 'unknown-tenant-id')
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
