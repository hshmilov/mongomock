import os
import re
import datetime

from collections import defaultdict, OrderedDict
from typing import List

import matplotlib
import matplotlib.pyplot as plt


# pylint: disable=anomalous-backslash-in-string
def get_points_from_build_log():
    with open('test.txt', 'rt') as f:
        x = f.read().strip()

    jobs = defaultdict(dict)

    real_start = None
    for line in x.splitlines():
        try:
            groups = re.search('\[(.*)\]\[.*\] (.*)\: executing (.*):.*', line.strip()).groups()
            if not any(groups[2].lower().startswith(sw) for sw in ['ui', 'parallel', 'integ', 'unit']):
                continue

            start, node, test = groups

            hours, minutes, seconds = start.split(':')
            start = datetime.timedelta(
                hours=int(hours), minutes=int(minutes), seconds=int(seconds)
            )

            if not real_start:
                real_start = start

            jobs[groups[2]] = {
                'start': start - real_start,
                'node': node,
                'test': test
            }
        except Exception:
            pass

        try:
            log_time, test_name, node, td = re.search('\[(.*)\]\[.*\] Finished with job (.*) on (.*) after (.*)',
                                                      line.strip()).groups()
            if not any(test_name.lower().startswith(sw) for sw in ['ui', 'parallel', 'integ', 'unit']):
                continue
            hours, minutes, seconds = td.split(':')
            jobs[test_name]['took'] = datetime.timedelta(
                hours=int(hours), minutes=int(minutes), seconds=int(seconds)
            )
        except Exception:
            pass

    jobs = OrderedDict(sorted(jobs.items(), key=lambda i: i[1].get('took') or datetime.timedelta(hours=3)))
    return jobs.values()


def generate_graph_from_lines(lines: List[dict], artifacts_path: str):
    print(f'Parsing {len(lines)}')
    fig = plt.figure(figsize=(50, 50))
    ax = fig.add_subplot(111)
    plt.title('Tests Time Distribution')
    plt.xlabel('Time since beginning')
    plt.ylabel('Tests')

    print(f'Starting')
    colors = dict()
    for i, item in enumerate(lines):
        start = item['start']
        took = item.get('took') or datetime.timedelta(hours=3)

        x1 = start.total_seconds()
        x2 = (start + took).total_seconds()

        if item['node'] not in colors:
            colors[item['node']] = 'blue'
        color = colors[item['node']]

        plt.plot([x1, x2], [i, i], linewidth=5, markersize=12, color=color)

    def timedelta_str(timedelta_str: dict):
        if 'took' not in timedelta_str:
            return 'Infinity'
        tdx = timedelta_str['took']
        return f'{str(tdx)}s'

    plt.yticks(
        range(len(lines)),
        [i['test'] + f'({timedelta_str(i)})' for i in lines]
    )

    def timeTicks(x, pos):
        d = datetime.timedelta(seconds=x)
        return str(d)

    formatter = matplotlib.ticker.FuncFormatter(timeTicks)
    ax.xaxis.set_major_formatter(formatter)

    plt.savefig(os.path.join(artifacts_path, 'tests_by_time.jpg'))
