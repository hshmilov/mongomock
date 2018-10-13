#!/usr/bin/env python3
import pathlib
import os
import glob
import dateutil.parser

all_log_lines = []

logs_location = str(pathlib.Path(os.path.dirname(__file__)) / '..' / '..' / '..' / 'logs')
for logfile in glob.iglob(logs_location + '/**/*axonius.log', recursive=True):
    for line in open(logfile).readlines():
        as_dict = eval(line)
        as_dict['ts'] = dateutil.parser.parse(as_dict['@timestamp'])
        all_log_lines.append(as_dict)

all_log_lines = sorted(all_log_lines, key=lambda l: l['ts'])

first_time = all_log_lines[0]['ts']
for line in all_log_lines:
    print(f"{(line['ts'] - first_time).total_seconds()}: {line['plugin_unique_name']} - {line['message']}")
