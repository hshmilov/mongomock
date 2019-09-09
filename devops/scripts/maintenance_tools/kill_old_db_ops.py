import sys
from typing import List
from testing.services.plugins.mongo_service import MongoService

mongo = MongoService().client


# This script allows showing and killing of DB operations that take too long


def get_old_ops(secs: int):
    db = mongo['aggregator']
    ops: List[dict] = db.current_op()['inprog']
    for op in ops:
        secs_running: int = op.get('secs_running') or 0
        if not isinstance(secs_running, int):
            continue
        if secs_running < secs:
            continue
        ns: str = op.get('ns')
        if not isinstance(ns, str):
            continue
        if 'aggregator' not in ns:
            continue
        yield op


def main(wet: bool, secs: int):
    print(f'Starting killing old ops {sys.argv[0]} wet: {wet}, that are running for secs {secs}')
    for op in get_old_ops(secs):
        con_id = op.get('connectionId')
        client_metadata = ((op.get('clientMetadata') or {}).get('driver') or {}).get('name') or '[None]'
        secs_running = op.get('secs_running')
        print(f'{con_id} by {client_metadata} is running for {secs_running}')
        if wet and client_metadata == 'PyMongo':
            killed = mongo['admin'].command({
                'killOp': 1,
                'op': con_id
            })
            print(f'to be killed {killed}')


if __name__ == '__main__':
    try:
        _, arg_wet, arg_secs = sys.argv
        arg_secs = int(arg_secs)
    except ValueError:
        print(f'usage: {sys.argv[0]} wet|dry time_in_seconds')
        sys.exit(-1)
    sys.exit(main(arg_wet == 'wet', arg_secs))
