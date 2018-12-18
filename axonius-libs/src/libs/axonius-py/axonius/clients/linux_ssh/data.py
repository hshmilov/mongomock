import logging
import re
# pylint: disable=deprecated-module
import string
# pylint: enable=deprecated-module

logger = logging.getLogger(f'axonius.{__name__}')

EMPTY_MAC = '00:00:00:00:00:00'


def kilo_to_giga(kilo):
    return round(float(kilo) / 1024 / 1024, 2)


def usage_percentage(all_, free):
    return float(round(((float(all_) - float(free)) / float(all_)) * 100, 2))


class AbstractCommand:
    COMMAND = None
    NAME = None

    def __init__(self, client_id, data):
        self._client_id = client_id
        self._raw_data = data
        self._parsed_data = {}

    def parse(self):
        try:
            self._parsed_data = self._parse(self._raw_data)
            return True
        except Exception:
            logger.exception(f'{self.get_name()} failed to parse')
        return False

    @staticmethod
    def _parse(raw_data):
        raise NotImplementedError()

    @classmethod
    def get_command(cls):
        return cls.COMMAND

    @classmethod
    def get_name(cls):
        return cls.NAME


class LocalInfoCommand(AbstractCommand):
    @staticmethod
    def calculate_id(client_id, device):
        device_dict = device.to_dict()

        hostname = device_dict.get('hostname')
        macs = [iface.get('mac') for iface in device_dict.get('network_interfaces', [])]
        return 'linux_ssh_' + '_'.join(sorted(filter(None, [client_id, hostname] + macs)))

    def to_axonius(self, device):
        curr_raw_data = device.get_raw()
        curr_raw_data[self.NAME] = {'raw_data': self._raw_data,
                                    'parsed_data': self._parsed_data}

        device.set_raw(curr_raw_data)

        device.id = self.calculate_id(self._client_id, device)

        if self._parsed_data:
            try:
                self._to_axonius(device, self._parsed_data)
                return True
            except Exception:
                logger.exception(f'{self.get_name()} failed to axonius')
        return False

    @staticmethod
    def _to_axonius(device, parsed_data):
        raise NotImplementedError()


class ForeignInfoCommand(AbstractCommand):
    def create_axonius_devices(self, create_device_callback):
        raise NotImplementedError()


class HostnameCommand(LocalInfoCommand):
    COMMAND = 'cat /etc/hostname'
    NAME = 'hostname'

    @staticmethod
    def _parse(raw_data):
        return raw_data

    @staticmethod
    def _to_axonius(device, parsed_data):
        device.hostname = parsed_data


class IfaceCommand(LocalInfoCommand):
    COMMAND = 'ip a'
    NAME = 'iface'

    @staticmethod
    def interface_list_iter(raw_data):
        result = []
        for line in raw_data.split('\n'):
            if result == []:
                result.append(line)
                continue

            if line and (line[0] not in string.whitespace):
                yield '\n'.join(result)
                result = []

            result.append(line)
        yield '\n'.join(result)

    @staticmethod
    def _parse(raw_data):
        parsed_data = []

        for interface in IfaceCommand.interface_list_iter(raw_data.strip()):
            parsed_iface = {}

            name_match = re.findall(r'(^\d*?):\s(\S*?):\s', interface)
            parsed_iface['index'] = name_match[0][0] if name_match else None
            parsed_iface['name'] = name_match[0][1] if name_match else None

            mtu_match = re.findall(r'mtu\s(\d*)\s', interface, re.DOTALL)
            parsed_iface['mtu'] = mtu_match[0] if mtu_match else None

            ipv4 = re.findall(r'inet\s(\S*)\s', interface, re.DOTALL)
            ipv6 = re.findall(r'inet6\s(\S*)\s', interface, re.DOTALL)

            parsed_iface['ipv4'] = ipv4
            parsed_iface['ipv6'] = ipv6

            mac_match = re.findall(r'link/\w*?\s(\S*)\s', interface, re.DOTALL)
            parsed_iface['mac'] = mac_match[0] if mac_match and mac_match[0] != EMPTY_MAC else None

            status_match = re.findall(r'state\s(\w*)\s', interface, re.DOTALL)
            parsed_iface['operational_status'] = status_match[0] if status_match else None

            parsed_data.append(parsed_iface)
        return parsed_data

    @staticmethod
    def _to_axonius(device, parsed_data):
        for interface in parsed_data:
            ips = [ip.split('/')[0] for ip in interface['ipv4']] + \
                  [ip.split('/')[0] for ip in interface['ipv6']]
            device.add_nic(name=interface['name'],
                           mac=interface['mac'],
                           ips=ips,
                           subnets=interface['ipv4'] + interface['ipv6'],
                           mtu=interface['mtu'],
                           operational_status=interface['operational_status'])


class HDCommand(LocalInfoCommand):
    COMMAND = 'df --output=source,fstype,size,avail,target'
    NAME = 'harddisk'

    @staticmethod
    def _parse(raw_data):
        fields_names = ('source', 'fstype', 'size', 'avail', 'target')
        result = []

        # skip headers go from 2nd line
        for line in raw_data.splitlines()[1:]:
            fields = re.findall(r'\s*(\S+)[\s]+(\S+)[\s]+(\d+)[\s]+(\d+)\s+(\S+)\s*',
                                line)
            if not fields:
                continue

            fields_dict = dict(zip(fields_names, fields[0]))
            fields_dict['size'] = kilo_to_giga(fields_dict['size'])
            fields_dict['avail'] = kilo_to_giga(fields_dict['avail'])

            result.append(fields_dict)
        return result

    @staticmethod
    def _to_axonius(device, parsed_data):
        for fs_data in parsed_data:
            device.add_hd(
                path=fs_data.get('target'),
                total_size=fs_data.get('size'),
                free_size=fs_data.get('avail'),
                file_system=fs_data.get('fstype'),
                device=fs_data.get('source'),
            )


class VersionCommand(LocalInfoCommand):
    COMMAND = 'uname -a'
    NAME = 'version'

    @staticmethod
    def _parse(raw_data):
        uname_string = raw_data
        raw_data = raw_data.split()
        kernel_version = raw_data[2] if len(raw_data) > 2 else None
        return {'kernel_version': kernel_version,
                'uname': uname_string}

    @staticmethod
    def _to_axonius(device, parsed_data):
        device.figure_os(parsed_data['uname'])
        device.os.kernel_version = parsed_data['kernel_version']


class DistroCommand(LocalInfoCommand):
    COMMAND = 'lsb_release -a'
    NAME = 'distro'

    @staticmethod
    def _parse(raw_data):
        result = {}
        codename = re.findall(r'Codename:\s*(\w+)', raw_data)
        distro = re.findall(r'Distributor ID:\s*(\w+)', raw_data)
        release = re.findall(r'Release:\s*(\w+)', raw_data)
        result['distro'] = distro[0] if distro else None
        result['release'] = release[0] if release else None
        result['codename'] = codename[0] if codename else None
        return result

    @staticmethod
    def _to_axonius(device, parsed_data):
        if parsed_data.get('distro'):
            device.os.distribution = parsed_data.get('distro')

        if any(parsed_data.values()):
            device.os.build = ' '.join(parsed_data.values())


class MemCommand(LocalInfoCommand):
    COMMAND = 'cat /proc/meminfo'
    NAME = 'mem'

    @staticmethod
    def _parse(raw_data):
        """ In linux there are 3 (intersting) memory related variables,
            total, available and free
            the difference between free and available is that free relates
            to the amount of memory that isn't in use at all by the system
            and available memory is the amount of memory that available for
            allocation. for now we discard free memory and will only show
            available memory as free RAM
        """
        result = {}
        mem_total = re.findall(r'MemTotal:\s*(\d+)\s+kB', raw_data)
        mem_available = re.findall(r'MemAvailable:\s*(\d+)\s+kB', raw_data)
        result['mem_total'] = kilo_to_giga(float(mem_total[0])) if mem_total else None
        result['mem_available'] = kilo_to_giga(float(mem_available[0])) if mem_available else None
        result['mem_percentage'] = usage_percentage(mem_total[0], mem_available[0]) \
            if mem_total and mem_available else None
        return result

    @staticmethod
    def _to_axonius(device, parsed_data):
        device.total_physical_memory = parsed_data['mem_total']
        device.free_physical_memory = parsed_data['mem_available']
        device.physical_memory_percentage = parsed_data['mem_percentage']


class DPKGCommand(LocalInfoCommand):
    """ this command is supported only for debian based system """
    COMMAND = 'dpkg -l | cat'
    NAME = 'dpkg'

    @staticmethod
    def _parse(raw_data):
        fields = ('name', 'version', 'architecture', 'description')

        packages_data = re.findall(r'ii\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)', raw_data)
        return [dict(zip(fields, package_data)) for package_data in packages_data]

    @staticmethod
    def _to_axonius(device, parsed_data):
        for software in parsed_data:
            device.add_installed_software(**software)


class UsersCommand(LocalInfoCommand):
    COMMAND = 'cat /etc/passwd'
    NAME = 'users'

    @staticmethod
    def _parse(raw_data):
        fields = ('name', 'password', 'userid', 'groupid', 'username/comment', 'homedir', 'interpreter')

        data = [line.split(':') for line in raw_data.splitlines()]

        return [dict(zip(fields, line)) for line in data if len(line) == len(fields)]

    @staticmethod
    def _to_axonius(device, parsed_data):
        for user in parsed_data:
            device.add_users(user_sid=user['userid'],
                             username=user['name'],
                             is_admin=user['userid'] == '0',
                             interpreter=user['interpreter'])


ALL_COMMANDS = [
    HostnameCommand,
    IfaceCommand,
    HDCommand,
    VersionCommand,
    DistroCommand,
    MemCommand,
    DPKGCommand,
    UsersCommand,
]
