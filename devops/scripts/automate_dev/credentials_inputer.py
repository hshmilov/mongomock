#!/usr/bin/env python3
from importlib import import_module
from multiprocessing.dummy import Pool as ThreadPool

from axonius.consts.plugin_consts import PLUGIN_NAME, PLUGIN_UNIQUE_NAME
from testing.services.axonius_service import AxoniusService


def main():
    system = AxoniusService()

    # credentials_inputer usually starts the adapters, and there's only so much adapters you can start in parallel
    pool = ThreadPool(10)

    adapters = {
        x[PLUGIN_NAME]: x
        for x
        in system.db.client['core']['configs'].find({
            'plugin_type': 'Adapter'
        })
    }

    def add_cred(name, current_service):
        try:
            adapter = current_service()

            adapter_data_from_db = adapters.get(adapter.plugin_name)
            if not adapter_data_from_db:
                return
            print(f'adding creds on {adapter.plugin_name}')

            if adapter_data_from_db['status'] == 'down':
                system.core.trigger(f'start:{adapter_data_from_db[PLUGIN_UNIQUE_NAME]}', blocking=True)

            if len(adapter.clients()) > 0:
                print('A Client Already exists')
            try:
                test_adapter_module = import_module(f'parallel_tests.test_{name}')
            except ModuleNotFoundError as ex:
                print(f'Could not find test service for {name}')
                return
            for atter, value in test_adapter_module.__dict__.items():
                if hasattr(value, 'some_client_details'):
                    test_adapter_service = value()
            if isinstance(test_adapter_service.some_client_details, list):
                for client in test_adapter_service.some_client_details:
                    adapter.add_client(client[0])
            else:
                adapter.add_client(test_adapter_service.some_client_details)
        except Exception as e:
            print(f'Error: {e} on {name}')

    pool.map(lambda x: add_cred(*x), system.get_all_adapters())


if __name__ == '__main__':
    main()
