#!/usr/bin/env python3

import sys
import json
import argparse
import time

from axonius.consts.scheduler_consts import Phases
from services.plugins.system_scheduler_service import SystemSchedulerService


def main(should_wait=False, seconds=600):
    system_scheduler = SystemSchedulerService()
    system_scheduler.start_research()

    if should_wait:
        waited = 10
        time.sleep(waited)  # because for some reason it takes time to change phase (AX-1832)
        while True:
            state = json.loads(system_scheduler.current_state().content)['Phase']
            if state == Phases.Stable.name:
                print('System phase stable')
                return
            else:
                print(f'System phase {state}')
                time.sleep(3)
                waited += 3
            if waited > seconds:
                raise TimeoutError()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait', action='store_true', default=False)
    parser.add_argument('-s', '--seconds', type=int, default=600)

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    main(args.wait, args.seconds)
