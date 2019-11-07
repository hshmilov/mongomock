#!/usr/bin/env python3
"""
take json log and convert it to raw_log
"""

import sys
import json
from dateutil.parser import parse


def main(filename='/dev/stdin'):

    with open(filename, 'rt') as f:
        while True:
            line = f.readline()
            if not line:
                break
            try:
                log = json.loads(line)
                log_level = log.get('level', '')
                log_message = log.get('message', '')
                log_timestamp = parse(log.get('@timestamp', '00:00')).strftime('%d/%m/%y %H:%M:%S:%f')
                log_exc_info = log.get('exc_info', '')
                log_exception_message = log.get('exception_message', '')
                if log_exception_message:
                    log_exception_message = '\n' + log_exception_message
                if log_exc_info:
                    log_exc_info = '\n' + log_exc_info
                print(f'{log_timestamp}  {log_level: <8} {log_message} {log_exc_info} {log_exception_message}')
            except Exception:
                print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
