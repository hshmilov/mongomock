#!/usr/bin/env python3
import os
import sys

from multiprocessing.dummy import Pool as ThreadPool
from devops.scripts.fast_axonius.fast_axonius import fast_axonius


def main():
    ax = fast_axonius()
    services = list(ax._services.values())
    pool = ThreadPool(len(services))

    def add_cred(current_service):
        if current_service.is_up():
            current_service.set_client()

    pool.map(add_cred, services)


if __name__ == '__main__':
    main()
