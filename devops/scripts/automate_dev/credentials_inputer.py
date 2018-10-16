#!/usr/bin/env python3
from multiprocessing.dummy import Pool as ThreadPool
from devops.scripts.fast_axonius.fast_axonius import fast_axonius


NUM_OF_WORKERS = 30


def main():
    ax = fast_axonius()
    services = list(ax._services.values())
    pool = ThreadPool(NUM_OF_WORKERS)

    def add_cred(current_service):
        if current_service.is_up() and hasattr(current_service, 'set_client'):
            current_service.set_client()

    pool.map(add_cred, services)


if __name__ == '__main__':
    main()
