#!/usr/bin/env python3
from importlib import import_module
from multiprocessing.dummy import Pool as ThreadPool

from testing.services.axonius_service import AxoniusService

NUM_OF_WORKERS = 30


def main():
    system = AxoniusService()

    services = system.get_all_adapters()

    pool = ThreadPool(NUM_OF_WORKERS)

    def add_cred(current_service):
        adapter = current_service[1]()
        if adapter.is_up():
            if len(adapter.clients()) > 0:
                print('A Client Already exists')

            try:
                test_adapter_module = import_module(f'parallel_tests.test_{current_service[0]}')
            except ModuleNotFoundError as ex:
                print(f'Could not find test service for {current_service[0]}')
                return

            for atter, value in test_adapter_module.__dict__.items():
                if hasattr(value, 'some_client_details'):
                    test_adapter_service = value()

            if isinstance(test_adapter_service.some_client_details, list):
                for client in test_adapter_service.some_client_details:
                    adapter.add_client(client[0])
            else:
                adapter.add_client(test_adapter_service.some_client_details)

    pool.map(add_cred, services)


if __name__ == '__main__':
    main()
