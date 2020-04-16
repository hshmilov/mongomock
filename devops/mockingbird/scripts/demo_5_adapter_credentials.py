#!/usr/bin/env python3
from multiprocessing.dummy import Pool as ThreadPool

from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME
from services.plugin_service import AdapterService
from testing.services.axonius_service import AxoniusService
from testing.services.adapters.aws_service import AwsService
from testing.services.adapters.cisco_meraki_service import CiscoMerakiService
from testing.services.adapters.eclypsium_service import EclypsiumService
from testing.services.adapters.counter_act_service import CounterActService
from testing.services.adapters.epo_service import EpoService
from testing.services.adapters.ad_service import AdService
from testing.services.adapters.azure_service import AzureService
from testing.services.adapters.sccm_service import SccmService
from testing.services.adapters.mobileiron_service import MobileironService
from testing.services.adapters.tenable_security_center_service import TenableSecurityCenterService
from testing.services.adapters.esx_service import EsxService


def main():
    # credentials_inputer usually starts the adapters, and there's only so much adapters you can start in parallel
    system = AxoniusService()
    pool = ThreadPool(5)

    adapters = {
        x[PLUGIN_NAME]: x
        for x
        in system.db.client['core']['configs'].find({
            'plugin_type': 'Adapter'
        })
    }

    def add_cred(adapter: AdapterService, creds: dict):
        try:
            adapter_data_from_db = adapters.get(adapter.plugin_name)
            if not adapter_data_from_db:
                return
            print(f'adding creds on {adapter.plugin_name}')

            if adapter_data_from_db['status'] == 'down':
                system.core.trigger(f'start:{adapter_data_from_db[PLUGIN_UNIQUE_NAME]}', blocking=True)

            if len(adapter.clients()) > 0:
                print(f'Adapter {adapter.plugin_name}: A Client Already exists')

            adapter.add_client(creds)
            print(f'Added for {adapter.plugin_name}')
        except Exception as e:
            print(f'Error: {e} for {adapter.plugin_name}')

    all_adapters = [
        (AwsService(), {
            "aws_access_key_id": 'JAKZM2LANLV9KA',
            "aws_secret_access_key": 'p',
            "region_name": "us-east-2",
            'get_all_regions': False
        }),
        (CiscoMerakiService(), {
            "CiscoMeraki_Domain": "https://meraki.demo.local",
            "apikey": "a",
            "verify_ssl": True,
        }),
        (EclypsiumService(), {
            'domain': 'https://eclypsium.demo.local',
            'verify_ssl': True,
            'client_id': '8nczak2m1apx0',
            'client_secret': 'p'
        }),
        (CounterActService(), {
            'domain': 'counteract.demo.local',
            'username': 'axonius-readonly',
            'password': 'p',
            'verify_ssl': True
        }),
        (EpoService(), {
            "host": "epo.demo.local",
            "port": 8443,
            "user": "axonius-readonly",
            "password": "p"
        }),
        (AdService(), {
            "user": "DEMO\\axoniusSvc",
            "password": "p",
            "dc_name": "demo.local",
            "use_ssl": "Unverified"
        }),
        (AzureService(), {
            'client_id': '1aa98e13-cdbb-41c8-818c-6a9cce91cac2',
            'client_secret': 'p',
            'tenant_id': 'a02ea21a-a415-411a-98ca-23d368271a4b',
            'subscription_id': 'ca998321-c712-4de2-bb72-c81726a5b124',
            'verify_ssl': True
        }),
        (SccmService(), {
            "server": "sccm.demo.local",
            'port': 1433,
            'database': 'CM_DEMO',
            "username": "axonius-readonly",
            "password": "p",
        }),
        (MobileironService(), {
            "domain": "https://m.mobileiron.net",
            "username": "axonius-readonly",
            "password": "p",
            "verify_ssl": True,
            "url_base_path": "axonius-demo"
        }),
        (TenableSecurityCenterService(), {
            "url": "tenablesc.demo.local",
            "username": "axonius-readonly",
            "password": "p",
            "verify_ssl": True
        }),
        (EsxService(), {
            "host": "vcenter.demo.local",
            "user": "axonius-readonly@demo.local",
            "password": "p",
            "verify_ssl": True,
            "rest_api": "https://vcenter.demo.local/api",
        }),
    ]
    pool.map(lambda x: add_cred(*x), all_adapters)
    print(f'Done')


if __name__ == '__main__':
    main()
