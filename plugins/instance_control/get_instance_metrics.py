import json
import os
import subprocess
import psutil
import docker
import netifaces

SWAP_CACHED_COMMAND = 'awk \'/SwapCached/{print $(NF-1)}\' /proc/meminfo'
CPU_PHYSICAL_CORES_COMMAND = 'lscpu | grep -E \"Socket\" | awk \'{print $2}\''
INTERFACE_FILTER_LIST = ['lo', 'docker', 'veth', 'weave', 'datapath', 'vxlan', 'dummy', 'br-ax-docker', 'vpnnet']


def main():
    result = {
        'metrics': {
            'ips': '',
            'memory_free_space': 0,
            'memory_size': 0,
            'swap_size': 0,
            'swap_free_space': 0,
            'swap_cache_size': 0,
            'data_disk_free_space': 0,
            'os_disk_free_space': 0,
            'data_disk_size': 0,
            'os_disk_size': 0,
            'cpu_usage': 0,
            'physical_cpu': 0,
            'cpu_cores': 0,
            'cpu_core_threads': 0,
            'last_snapshot_size': 0,
            'max_snapshots': 0,
            'remaining_snapshots_days': 0
        },
        'errors': []
    }

    try:
        get_disk_space(result)
        get_ips(result)
        get_mem_info(result)
        get_swap_info(result)
        get_cpu_info(result)
    except Exception as e:
        result['errors'].append({'command': 'main', 'error': str(e)})

    # pylint: disable=unnecessary-lambda
    print(json.dumps(result, indent=4, sort_keys=True, default=lambda o: str(o)))


def bytes_to_kb(value):
    return value / 1024


def get_disk_space(result):
    try:
        client = docker.from_env()
        mongo_volume = client.volumes.get('mongo_data').attrs['Mountpoint']
        path = mongo_volume.split('docker')[0]

        data_drive = os.stat(path).st_dev
        os_drive = os.stat('/').st_dev

        usage = psutil.disk_usage(path)
        if data_drive == os_drive:
            result['metrics']['data_disk_free_space'] = round(bytes_to_kb(usage.free))
            result['metrics']['data_disk_size'] = round(bytes_to_kb(usage.total))
        else:
            os_usage = psutil.disk_usage(path)
            result['metrics']['os_disk_free_space'] = round(bytes_to_kb(os_usage.free))
            result['metrics']['os_disk_size'] = round(bytes_to_kb(os_usage.total))

    except Exception as e:
        result['errors'].append(str(e))


# pylint: disable=I1101
def get_ips(result):
    ips = []

    def append_ip_address(address_object):
        specific_ip = address_object.get('addr')
        if specific_ip and not specific_ip.startswith('127.0'):
            ips.append(specific_ip)

    try:
        # parsing the private ips.
        for iface in netifaces.interfaces():
            if not any(x in iface for x in INTERFACE_FILTER_LIST):
                addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET)
                if addrs and len(addrs) > 0:
                    for address in addrs:
                        append_ip_address(address)
        result['metrics']['ips'] = ips
    except Exception as e:
        result['errors'].append({'command': 'ips', 'error': str(e)})


def get_mem_info(result):
    try:
        mem_info = psutil.virtual_memory()
        result['metrics']['memory_size'] = bytes_to_kb(mem_info.total)
        result['metrics']['memory_free_space'] = bytes_to_kb(mem_info.free)
    except Exception as e:
        result['errors'].append({'command': 'mem_info', 'error': str(e)})


def get_swap_info(result):
    try:
        mem_info = psutil.swap_memory()
        result['metrics']['swap_size'] = round(bytes_to_kb(mem_info.total))
        result['metrics']['swap_free_space'] = round(bytes_to_kb(mem_info.free))

        process = subprocess.Popen(SWAP_CACHED_COMMAND, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderror = process.communicate()
        if stdout and not stderror:
            result['metrics']['swap_cache_size'] = round(bytes_to_kb(int(stdout)))
    except Exception as e:
        result['errors'].append({'command': 'swap_info', 'error': str(e)})


def get_cpu_info(result):
    try:
        process = subprocess.Popen(CPU_PHYSICAL_CORES_COMMAND, shell=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderror = process.communicate()
        if stdout and not stderror:
            result['metrics']['physical_cpu'] = int(stdout)
        result['metrics']['cpu_cores'] = psutil.cpu_count(logical=False)
        result['metrics']['cpu_core_threads'] = round(psutil.cpu_count() / psutil.cpu_count(logical=False))
        result['metrics']['cpu_usage'] = round(psutil.cpu_percent())
    except Exception as e:
        result['errors'].append({'command': 'cpu_info', 'error': str(e)})


if __name__ == '__main__':
    main()
