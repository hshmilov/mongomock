#!/usr/bin/env python3

import sys
import argparse
import time
from datetime import datetime
from system_consts import NODE_MARKER_PATH

from axonius.consts.scheduler_consts import Phases
from services.plugins.system_scheduler_service import SystemSchedulerService


WAIT_TIMEOUT = 60 * 25


def main(should_wait=False, seconds=WAIT_TIMEOUT):
    if NODE_MARKER_PATH.exists():
        print('This instance is a node - Skipping')
        return

    system_scheduler = SystemSchedulerService()
    system_scheduler.start_research()

    if should_wait:
        waited = 10
        time.sleep(waited)  # because for some reason it takes time to change phase (AX-1832)
        while True:
            try:
                state = system_scheduler.current_state().json()

                # this API has changed it signature over 1.10->1.11, therefore this code should support both
                if 'state' in state:
                    state = state['state']

                state = state['Phase']
                if state == Phases.Stable.name:
                    print('System phase stable')
                    return
                print(f'System phase {state} at {datetime.now()}')
            except Exception as e:
                print(f'Error on {repr(e)} discover_now')
            time.sleep(3)
            waited += 3
            if waited > seconds:
                raise TimeoutError()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait', action='store_true', default=False)
    parser.add_argument('-s', '--seconds', type=int, default=WAIT_TIMEOUT)

    try:
        args = parser.parse_args()
    except AttributeError:
        print(parser.usage())
        sys.exit(1)

    main(args.wait, args.seconds)
