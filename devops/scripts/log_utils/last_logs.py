#!/usr/bin/env python3
import glob
import os
import pathlib
import pprint
import json
import argparse
from logging import _nameToLevel
import io


def get_logs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--max_lines", default=10, help="Number of most recent lines to fetch")
    parser.add_argument("-l", "--min_level", default='WARNING', help="Minimal severity")
    parser.add_argument("-f", "--filter", default='', help="Filename filter")
    parser.add_argument("-d", "--log_dir",
                        default=str(pathlib.Path(os.path.dirname(__file__)) / '..' / '..' / '..' / 'logs'),
                        help="Alternative logs location")
    parser.add_argument('--json', action='store_true', default=False, help='Output as json')

    args = parser.parse_args()

    min_level = _nameToLevel[args.min_level]
    max_lines = int(args.max_lines)
    filter_exp = args.filter
    as_json = args.json
    log_dir = args.log_dir

    result = {}
    for filename in glob.iglob(log_dir + '/**/*axonius.log', recursive=True):

        if filter_exp not in filename:
            continue

        ll = []
        with open(filename, 'rb') as logfile:

            last_lines = logfile.readlines()
            last_lines.reverse()
            for line in last_lines:
                line = json.loads(line)

                if _nameToLevel[line['level']] < min_level:
                    continue

                ll.insert(0, line)

                if len(ll) >= max_lines:
                    break

        if len(ll) > 0:
            result[os.path.basename(filename).replace('_axonius.log', '').replace('_adapter', '')] = ll

    if as_json:
        return json.dumps(result, indent=1)
    else:
        out = io.StringIO()
        pprint.pprint(result, stream=out)
        return out.getvalue()


if __name__ == '__main__':
    print(get_logs())
