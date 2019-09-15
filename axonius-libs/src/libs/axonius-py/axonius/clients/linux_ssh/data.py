import logging
import re
import shlex

# pylint: disable=no-name-in-module
from distutils import version
# pylint: enable=no-name-in-module
from typing import Callable, List
# pylint: disable=deprecated-module
import string
# pylint: enable=deprecated-module
from axonius.devices.device_adapter import AdapterProperty, DeviceAdapter, ListField
from axonius.fields import Field

logger = logging.getLogger(f'axonius.{__name__}')

EMPTY_MAC = '00:00:00:00:00:00'


class LinuxDeviceAdapter(DeviceAdapter):
    md5_files_list = ListField(str, 'MD5 Files List')


def kilo_to_giga(kilo):
    return round(float(kilo) / 1024 / 1024, 2)


def megahertz_to_giga(mega):
    return round(float(mega) / 1000, 2)


def usage_percentage(all_, free):
    return float(round(((float(all_) - float(free)) / float(all_)) * 100, 2))


def add_version(device, release):
    # XXX: add regex to capture the version string from release
    try:
        major, minor, build = version.StrictVersion(release).version
        device.os.major = major
        device.os.minor = minor
        if build != 0:
            device.os.build = str(build)
    except ValueError:
        device.os.build = release


class AbstractCommand:
    COMMAND = ''
    STATIC_PATH = '/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin'
    END_MAGIC = 'OKOK'
    START_MAGIC = 'STARTSTART'
    CHECK_RET_VALUE = True
    REQUIRE_ROOT_PRIVILEGES = False

    def __init__(self):
        self._raw_data = ''
        self._parsed_data = {}

    def shell_execute(self, execute_callback: Callable[[str], str], password: str = None):
        """ factory to create the class given shell_execute function """
        shell_cmdline = self._get_command()

        # If we have password and the command require root privilege add sudo
        # if not, just try to execute it - maybe it will work
        if self.REQUIRE_ROOT_PRIVILEGES and password is not None:
            shell_cmdline = f'echo \'{password}\' | sudo -S sh -c \'{shell_cmdline}\''

        self._raw_data = execute_callback(shell_cmdline)

    def parse(self):
        try:
            self.assert_command_worked(self._raw_data)
            self._raw_data = self.strip_magic(self._raw_data)
            self._parsed_data = self._parse(self._raw_data)
            if not self._parsed_data:
                return False
            return True
        except Exception:
            logger.exception(f'{self.get_name()} failed to parse')
        return False

    @staticmethod
    def _parse(raw_data):
        raise NotImplementedError()

    def _get_command(self):
        """ we delete HISTFILE to make sure that we don't write passwords to history.
            In some distros such as redhat, non-interactive path is limited so we prepend
            default path. Add magic logic"""
        if self.CHECK_RET_VALUE:
            sep = '&&'
        else:
            sep = ';'

        command = f'echo -n {self.START_MAGIC} {sep} {self.COMMAND} {sep} echo -n {self.END_MAGIC}'
        command = f'HISTFILE=/dev/null PATH={self.STATIC_PATH}:$PATH {command}'

        return command

    @classmethod
    def get_name(cls):
        return cls.__name__

    @classmethod
    def assert_command_worked(cls, raw_data):
        if cls.START_MAGIC not in raw_data or cls.END_MAGIC not in raw_data:
            raise ValueError(f'Invalid command output {raw_data}')

    @classmethod
    def strip_magic(cls, raw_data):
        start = cls.START_MAGIC
        end = cls.END_MAGIC
        return raw_data[raw_data.index(start) + len(start):raw_data.index(end)]


class RmCommand(AbstractCommand):
    COMMAND = 'rm -f {filenames}'

    def __init__(self, filenames: List[str]):
        filenames = ' '.join([shlex.quote(file_) for file_ in filenames])
        self._filenames = filenames
        super().__init__()

    def _get_command(self):
        command = super()._get_command()
        command = command.format(filenames=self._filenames)
        return command

    def _parse(self, raw_data):
        return raw_data


class ChmodCommand(AbstractCommand):
    COMMAND = 'chmod {permissions} {filenames}'

    def __init__(self, permissions: int, filenames: List[str]):
        filenames = ' '.join([shlex.quote(file_) for file_ in filenames])
        self._filenames = filenames
        self._permissions = permissions
        super().__init__()

    def _get_command(self):
        command = super()._get_command()
        command = command.format(permissions=self._permissions, filenames=self._filenames)
        return command

    def _parse(self, raw_data):
        return raw_data


class LocalInfoCommand(AbstractCommand):

    @staticmethod
    def calculate_id(client_id, device):
        device_dict = device.to_dict()

        hostname = device_dict.get('hostname')
        macs = [iface.get('mac') for iface in device_dict.get('network_interfaces', [])]
        return 'linux_ssh_' + '_'.join(sorted(filter(None, [client_id, hostname] + macs)))

    def to_axonius(self, client_id, device):
        curr_raw_data = device.get_raw()
        curr_raw_data[self.get_name()] = {'raw_data': self._raw_data,
                                          'parsed_data': self._parsed_data}

        device.set_raw(curr_raw_data)

        device.id = self.calculate_id(client_id, device)

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


class MD5FilesCommand(LocalInfoCommand):
    COMMAND = 'md5sum {filenames}'
    CHECK_RET_VALUE = False

    def __init__(self, filenames: str):
        filenames = ' '.join([shlex.quote(file_) for file_ in filenames.split(',')])
        self._filenames = filenames
        super().__init__()

    def _get_command(self):
        command = super()._get_command()
        command = command.format(filenames=self._filenames)
        return command

    @staticmethod
    def _parse(raw_data):
        return re.findall(r'^([0-9a-fA-F]{32})\s*(.*)$', raw_data.strip(), re.MULTILINE)

    @staticmethod
    def _to_axonius(device, parsed_data):
        for hash_, filename in parsed_data:
            device.md5_files_list.append(f'{filename}: {hash_}')


class DynamicFieldCommand(LocalInfoCommand):
    COMMAND = '{command}'
    CHECK_RET_VALUE = False

    def __init__(self, field_name: str, command: str):
        self._command = command
        self._field_name = field_name.strip()
        self._normalized_field_name = field_name.strip().lower().replace(' ', '_').replace('-', '_')
        super().__init__()

    def _get_command(self):
        command = super()._get_command()
        command = command.format(command=self._command)
        return command

    @staticmethod
    def _parse(raw_data):
        return raw_data

    def _to_axonius(self, device, parsed_data):
        if not device.does_field_exist(self._normalized_field_name):
            field = Field(str, f'Linux {self._field_name}')
            device.declare_new_field(self._normalized_field_name, field)
        device[self._normalized_field_name] = str(parsed_data)


class ForeignInfoCommand(AbstractCommand):
    def create_axonius_devices(self, create_device_callback):
        raise NotImplementedError()


class HostnameCommand(LocalInfoCommand):
    COMMAND = 'uname -n'

    @staticmethod
    def _parse(raw_data):
        return raw_data.strip()

    @staticmethod
    def _to_axonius(device, parsed_data):
        device.hostname = parsed_data


class IfaceCommand(LocalInfoCommand):
    COMMAND = '/sbin/ip a'

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
            try:
                ips = [ip.split('/')[0] for ip in interface['ipv4']] + \
                      [ip.split('/')[0] for ip in interface['ipv6']]
                device.add_nic(name=interface['name'],
                               mac=interface['mac'],
                               ips=ips,
                               subnets=interface['ipv4'] + interface['ipv6'],
                               mtu=interface['mtu'],
                               operational_status=interface['operational_status'])
            except Exception as e:
                logger.exception('Failed to add interface')


class HDCommand(LocalInfoCommand):
    COMMAND = 'df -T'

    @staticmethod
    def _parse(raw_data):
        fields_names = ('source', 'fstype', 'size', 'use', 'avail', 'percent', 'target')

        result = []

        # skip headers go from 2nd line
        for line in raw_data.splitlines()[1:]:
            fields = re.findall(r'\s*(\S+)[\s]+(\S+)[\s]+(\d+)[\s]+(\d+)\s+(\d+)\s+(\d+%)\s+(\S+)\s*',
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
            try:
                device.add_hd(
                    path=fs_data.get('target'),
                    total_size=fs_data.get('size'),
                    free_size=fs_data.get('avail'),
                    file_system=fs_data.get('fstype'),
                    device=fs_data.get('source'),
                )
            except Exception as e:
                logger.exception('Failed to add interface')


class VersionCommand(LocalInfoCommand):
    COMMAND = 'uname -a'

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


class DebianDistroCommand(LocalInfoCommand):
    COMMAND = 'lsb_release -a'

    @staticmethod
    def _parse(raw_data):
        result = {}
        codename = re.findall(r'Codename:\s*(\w+)', raw_data)
        distro = re.findall(r'Distributor ID:\s*(\w+)', raw_data)
        release = re.findall(r'Release:\s*(\S+)', raw_data)
        result['distro'] = distro[0] if distro else None
        result['release'] = release[0] if release else None
        result['codename'] = codename[0] if codename else None
        return result

    @staticmethod
    def _to_axonius(device, parsed_data):
        if parsed_data.get('distro'):
            device.os.distribution = parsed_data.get('distro')

        if parsed_data.get('release'):
            add_version(device, parsed_data.get('release'))

        if parsed_data.get('codename'):
            device.os.codename = parsed_data.get('codename')


class RedHatDistroCommand(LocalInfoCommand):
    COMMAND = 'cat /etc/redhat-release'

    @staticmethod
    def _parse(raw_data):
        result = {}
        data = raw_data.split(' release ')

        if len(data) != 2:
            return result

        distro, data = data
        result['distro'] = distro.strip()

        data = data.strip().split(' ')
        if len(data) != 2:
            return result

        release, codename = data

        codename = codename.strip()

        if codename[0] == '(' and codename[-1] == ')':
            codename = codename[1:-1]

        result['release'] = release.strip()
        result['codename'] = codename.strip()

        return result

    @staticmethod
    def _to_axonius(device, parsed_data):
        if parsed_data.get('distro'):
            device.os.distribution = parsed_data.get('distro')

        if parsed_data.get('release'):
            add_version(device, parsed_data.get('release'))

        if parsed_data.get('codename'):
            device.os.codename = parsed_data.get('codename')


class MemCommand(LocalInfoCommand):
    COMMAND = 'cat /proc/meminfo'

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

    @staticmethod
    def _parse(raw_data):
        fields = ('name', 'version', 'architecture', 'description')

        packages_data = re.findall(r'ii\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)', raw_data)
        return [dict(zip(fields, package_data)) for package_data in packages_data]

    @staticmethod
    def _to_axonius(device, parsed_data):
        for software in parsed_data:
            try:
                device.add_installed_software(**software)
            except Exception as e:
                logger.error('failed to add installed software')


class RPMCommand(LocalInfoCommand):
    COMMAND = 'rpm -qa  --qf \'%{NAME}|%{VERSION}|%{ARCH}|%{SUMMARY}|%{VENDOR}\\n\''

    @staticmethod
    def _parse(raw_data):
        fields = ('name', 'version', 'architecture', 'description', 'vendor')
        packages_data = re.findall(r'(.*)\|(.*)\|(.*)\|(.*)\|(.*)', raw_data)
        return [dict(zip(fields, package_data)) for package_data in packages_data]

    @staticmethod
    def _to_axonius(device, parsed_data):
        for software in parsed_data:
            try:
                device.add_installed_software(**software)
            except Exception as e:
                logger.error('Failed to add installed software')


class UsersCommand(LocalInfoCommand):
    COMMAND = 'cat /etc/passwd'

    @staticmethod
    def _parse(raw_data):
        fields = ('name', 'password', 'userid', 'groupid', 'username/comment', 'homedir', 'interpreter')

        data = [line.split(':') for line in raw_data.splitlines()]

        return [dict(zip(fields, line)) for line in data if len(line) == len(fields)]

    @staticmethod
    def _to_axonius(device, parsed_data):
        for user in parsed_data:
            try:
                device.add_users(user_sid=user['userid'],
                                 username=user['name'],
                                 is_admin=user['userid'] == '0',
                                 is_local=True,
                                 interpreter=user['interpreter'])
            except Exception as e:
                logger.error('Failed to add user')


class HardwareCommand(LocalInfoCommand):
    COMMAND = 'dmidecode'
    REQUIRE_ROOT_PRIVILEGES = True

    @staticmethod
    def add_info_to_json(json, name, handle):
        result = re.findall(r'{0}:\s+(.*)\n'.format(name), handle)
        if not result:
            return

        result = result[0]
        if any(string.lower() == result.lower() for string in ('Not Present',
                                                               'Not Provided',
                                                               'Not Specified',
                                                               'None',
                                                               'Other',
                                                               'Unspecified',
                                                               'To Be Filled By O.E.M.')):
            return

        name = name.lower().replace(' ', '_')
        json[name] = result

    @staticmethod
    def _parse(raw_data):
        result = []
        handlers = re.findall(r'Handle .*?\n\n', raw_data, re.DOTALL)
        for raw_handle in handlers:
            parsed_handle = {}
            category = raw_handle.splitlines()

            if len(category) < 1:
                continue

            category = category[1]
            category = category.lower().replace(' ', '_')

            parsed_handle['category'] = category

            HardwareCommand.add_info_to_json(parsed_handle, 'Version', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Revision', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Vendor', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Serial Number', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Name', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'UUID', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Manufacturer', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Release Date', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Family', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Type', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Core Count', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Thread Count', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Current Speed', raw_handle)
            HardwareCommand.add_info_to_json(parsed_handle, 'Capacity', raw_handle)
            result.append(parsed_handle)
        return result

    @staticmethod
    def detect_properties(device, parsed_data):
        """ try to detect if the device is cloud/VM/etc by signing on the hardware
            based on my own exprience,
            https://unix.stackexchange.com/questions/89714/easy-way-to-determine-virtualization-technology"""
        cloud_signitures = ('Google Compute Engine',
                            'GoogleCloud',
                            'amazon')

        vm_signitures = ('VMware',
                         'VirtualBox',
                         'Virtual Machine')

        for signiture in cloud_signitures:
            if signiture in str(parsed_data):
                device.adapter_properties = [AdapterProperty.Manager,
                                             AdapterProperty.Assets,
                                             AdapterProperty.Cloud_Provider]
                return

        for signiture in vm_signitures:
            if signiture in str(parsed_data):
                device.adapter_properties = [AdapterProperty.Manager,
                                             AdapterProperty.Assets,
                                             AdapterProperty.Virtualization]
                return

    @staticmethod
    def _to_axonius(device, parsed_data):
        parsed_bios = False
        parsed_system_information = False
        parsed_base_board_information = False

        HardwareCommand.detect_properties(device, parsed_data)

        for handle in parsed_data:
            try:
                if handle['category'] == 'bios_information' and not parsed_bios:

                    try:
                        ver = handle.get('version')
                        version.StrictVersion(ver)
                        device.bios_version = ver
                    except ValueError:
                        try:
                            rev = handle.get('revision')
                            version.StrictVersion(ver)
                            if ver and rev and rev in ver:
                                device.bios_version = ver
                            else:
                                device.bios_version = rev
                        except ValueError:
                            device.bios_version = handle.get('version')

                    device.bios_serial = handle.get('serial')
                    parsed_bios = True

                if handle['category'] == 'system_information' and not parsed_system_information:
                    device.device_serial = handle.get('serial_number')
                    device.device_model = handle.get('name')
                    device.device_model_family = handle.get('family')
                    device.device_manufacturer = handle.get('manufacturer')
                    parsed_system_information = True

                if handle['category'] == 'base_board_information' and not parsed_base_board_information \
                        and handle.get('type', '').lower() == 'motherboard':
                    device.motherboard_serial = handle.get('serial')
                    device.motherboard_model = handle.get('name')
                    device.motherboard_version = handle.get('version')
                    device.motherboard_manufacturer = handle.get('manufacturer')
                    parsed_base_board_information = True

                if handle['category'] == 'processor_information':
                    ghz = None
                    try:
                        ghz = megahertz_to_giga(float(handle.get('current_speed').split(' ')[0]))
                    except Exception as e:
                        logger.exception(r'Failed to parse ghz')

                    device.add_cpu(name=handle.get('version'),
                                   manufacturer=handle.get('manufacturer'),
                                   family=handle.get('family'),
                                   cores=handle.get('core_count'),
                                   cores_thread=handle.get('thread_count'),
                                   ghz=ghz)

                if handle['category'] == 'portable_battery':
                    device.add_battery(model=handle.get('name'),
                                       capacity=handle.get('capacity'),
                                       manufacturer=handle.get('manufacturer'))
            except Exception as e:
                logger.exception('Failed to handle {handle}')


class ConcateCommands:
    """ class helper to specify that commands should run one after anoter,
        This is usefull for the day that we want to parallel the functionality """

    def __init__(self,
                 commands: List,
                 should_stop_on_first_error=False,
                 should_stop_on_first_success=False):
        self.commands = commands
        self.should_stop_on_first_error = should_stop_on_first_error
        self.should_stop_on_first_success = should_stop_on_first_success


class CommandExecutor:
    """ gets execute functions callback and client id, and handles all the command execution """

    ALL_COMMANDS = [
        HostnameCommand(),
        IfaceCommand(),
        HDCommand(),

        # Distro command assume that version command already finished
        ConcateCommands([
            VersionCommand(),
            ConcateCommands([
                DebianDistroCommand(),
                RedHatDistroCommand()
            ], should_stop_on_first_success=True),
        ]),
        MemCommand(),

        # DPKG is debian only if failed try RPM
        ConcateCommands([
            DPKGCommand(),
            RPMCommand(),
        ], should_stop_on_first_success=True),
        UsersCommand(),
        HardwareCommand(),
    ]

    def __init__(self, shell_execute: Callable[[str], str], password: str = None):
        self._shell_execute = shell_execute
        self._password = password
        self._dynamic_commands = []

    def add_dynamic_command(self, command):
        self._dynamic_commands.append(command)

    def handle_concated_commands(self, concated):
        parsed = False

        for command in concated.commands:
            if isinstance(command, ConcateCommands):
                parsed = yield from self.handle_concated_commands(command)
            else:
                parsed = yield from self.yield_command(command)

            if parsed and concated.should_stop_on_first_success:
                break

            if not parsed and concated.should_stop_on_first_error:
                break

        return parsed

    def yield_command(self, command, dynamic_cmd=None):
        result = False
        try:
            command.shell_execute(self._shell_execute, self._password)
            if command.parse():
                result = True
            yield command
        except Exception as e:
            logger.exception(f'Failed to execute command {command}')
        return result

    def get_commands(self):
        for command in self.ALL_COMMANDS + self._dynamic_commands:
            try:
                if isinstance(command, ConcateCommands):
                    yield from self.handle_concated_commands(command)
                else:
                    yield from self.yield_command(command)
            except Exception as e:
                logger.exception(f'get_commands {command} failed')
