
def splunk_split_symantec_mac(raw):
    cells = raw.split(',')
    d = {'type': 'symantec_mac',
         'timestamp': cells[0],
         'level': cells[1],
         'name': cells[2],
         'device': cells[5],
         'local ips': cells[6].split(': ', 1)[1],
         'local mac': cells[7].split(': ', 1)[1],
         'remote ips': cells[9].split(': ', 1)[1],
         'remote mac': cells[10].split(': ', 1)[1],
         'user': cells[19].split(': ', 1)[1],
         'domain': cells[20].split(': ', 1)[1],
         'raw': raw}
    return d


def splunk_split_symantec_win(raw):
    cells = raw.split(',', 5)
    endpoint_data = cells[-1]

    network_raw = get_item(endpoint_data, 'Network  info: ')
    items = network_raw.split('  ')
    d = {'type': 'symantec_win',
         'timestamp': cells[0],
         'level': cells[1],
         'name': cells[2],
         'category': cells[3].split(': ', 1)[1],
         'engine': endpoint_data.split('  ', 1)[0],
         'windows_version_info': get_item(endpoint_data, 'Windows Version info: ', ' Operating System:'),
         'os': get_item(endpoint_data, 'Operating System: ', ' Network  info:'),
         'network_raw': network_raw,
         'network': [],
         'raw': raw}
    for i in range(0, len(items), 4):
        d['network'].append({'index': items[i][4:],
                             'name': items[i + 1][1:-1],
                             'mac': items[i + 2],
                             'desc': items[i + 3].split("' ", 1)[0][1:-1],
                             'ip': items[i + 3].split("' ", 1)[1]})
    return d


def get_item(data, start, stop=None):
    if stop is not None:
        stop = data.find(stop)
    return data[data.find(start) + len(start): stop]
