# pylint: disable=wildcard-import
from axonius.clients.linux_ssh.mock import *
from axonius.clients.linux_ssh.data import LinuxDeviceAdapter


def test_hostname():
    device = LinuxDeviceAdapter(set(), set())

    command = HostnameMock()
    command.shell_execute()
    assert command.parse()
    assert command.to_axonius('test_hostname', device)

    assert device.id == 'linux_ssh_test_hostname'
    assert device.hostname == HostnameMock.RAW_DATA

# pylint: disable=protected-access


def test_interfaces():
    num_of_ifaces = 17
    indexes = list(map(str, (1, 2, 3, 4, 5, 6, 169, 171, 173, 175, 177, 179, 181, 183, 185, 200, 214)))
    mtus = ['65536'] + (['1500'] * (num_of_ifaces - 1))
    names = ['lo', 'wlp2s0', 'br-1272e8efd44d', 'docker0', 'virbr0', 'virbr0-nic',
             'veth0e392c6@if168', 'veth62a4919@if170', 'veth3e745c8@if172',
             'veth629784a@if174', 'vethc9bba02@if176', 'veth76ae783@if178',
             'veth72a8481@if180', 'veth76b395f@if182', 'vethbc02c13@if184',
             'enx1065300854a4', 'veth245c75e@if213']
    num_of_ipaddresses = 19

    device = LinuxDeviceAdapter(set(), set())
    command = IfaceMock()
    command.shell_execute()
    assert command.parse()
    assert command.to_axonius('test_iface', device)

    assert list(map(lambda x: x['index'], command._parsed_data)) == indexes

    axon_ifaces = device.to_dict()['network_interfaces']
    assert len(axon_ifaces) == num_of_ifaces
    assert [iface['mtu'] for iface in axon_ifaces] == mtus
    assert [iface['name'] for iface in axon_ifaces] == names
    assert all([iface['mac'] for iface in axon_ifaces if iface['name'] != 'lo'])
    assert all([iface['operational_status'] for iface in axon_ifaces])
    assert len(sum([iface.get('ips', []) for iface in axon_ifaces], [])) == num_of_ipaddresses


def test_hd():
    device = LinuxDeviceAdapter(set(), set())
    command = HDMock()
    command.shell_execute()
    assert command.parse()
    assert command.to_axonius('test_hd', device)
    assert len(device.to_dict()['hard_drives']) == 9
    assert device.to_dict()['hard_drives'][0] == {'path': '/dev', 'total_size': 7.68,
                                                  'free_size': 7.68, 'file_system': 'devtmpfs', 'device': 'udev'}


def test_debian_version_distro():
    device = LinuxDeviceAdapter(set(), set())
    command = VersionMock()
    command.shell_execute()
    command2 = DebianDistroMock()
    command2.shell_execute()
    assert command.parse()
    assert command2.parse()
    assert command.to_axonius('test_version', device)
    assert command2.to_axonius('test_distro', device)
    assert device.to_dict()['os']['kernel_version']
    assert device.to_dict()['os']['bitness'] == 64
    assert device.to_dict()['os']['distribution'] == 'Debian'
    assert device.to_dict()['os']['build'] == 'testing'
    assert device.to_dict()['os']['codename'] == 'buster'


def test_redhat_version_distro():
    device = LinuxDeviceAdapter(set(), set())
    command = VersionMock()
    command.shell_execute()
    command2 = RedHatDistroMock()
    command2.shell_execute()
    assert command.parse()
    assert command2.parse()
    assert command.to_axonius('test_version', device)
    assert command2.to_axonius('test_distro', device)
    assert device.to_dict()['os']['kernel_version']
    assert device.to_dict()['os']['bitness'] == 64
    assert device.to_dict()['os']['distribution'] == 'Red Hat Enterprise Linux Server'
    assert device.to_dict()['os']['codename'] == 'Santiago'
    assert device.to_dict()['os']['major'] == 6


def test_mem():
    device = LinuxDeviceAdapter(set(), set())
    command = MemMock()
    command.shell_execute()
    assert command.parse()
    assert command.to_axonius('test_mem', device)
    assert device.to_dict()['total_physical_memory'] == 15.39
    assert device.to_dict()['free_physical_memory'] == 7.19
    assert device.to_dict()['physical_memory_percentage'] == 53.27


def test_dpkg():
    device = LinuxDeviceAdapter(set(), set())
    command = DPKGMock()
    command.shell_execute()
    assert command.parse()
    assert command.to_axonius('test_dpkg', device)
    assert 'installed_software' in device.all_fields_found
    assert len(device.to_dict()['installed_software']) == 11


def test_rpm():
    device = LinuxDeviceAdapter(set(), set())
    command = RPMMock()
    command.shell_execute()
    assert command.parse()
    assert command.to_axonius('test_dpkg', device)
    assert 'installed_software' in device.all_fields_found
    assert len(device.to_dict()['installed_software']) == 23


def test_users():
    device = LinuxDeviceAdapter(set(), set())
    command = UsersMock()
    command.shell_execute()
    assert command.parse()
    assert command.to_axonius('test_users', device)
    assert len(device.to_dict()['users']) == 44
    assert len(list(filter(lambda user: user['is_admin'], device.to_dict()['users']))) == 1


def test_raw_data():
    device = LinuxDeviceAdapter(set(), set())

    command = HostnameMock()
    command.shell_execute()
    assert command.parse()
    command2 = IfaceMock()
    command2.shell_execute()
    assert command2.parse()
    assert command.to_axonius('test_hostname', device)
    assert command2.to_axonius('test_hostname', device)
    assert [command.get_name(), command2.get_name()] == list(device.to_dict()['raw'].keys())


def test_concat():
    device = LinuxDeviceAdapter(set(), set())
    executor = ConcatCommandFailMockExecutor()
    for command in executor.get_commands():
        command.to_axonius('test', device)
    assert len(device.to_dict()['raw'].keys()) == 3
    assert device.to_dict()['os']['codename'] == 'Santiago'

    device = LinuxDeviceAdapter(set(), set())
    executor = ConcatCommandSuccessMockExecutor()
    for command in executor.get_commands():
        command.to_axonius('test', device)
    assert len(device.to_dict()['raw'].keys()) == 2


def test_hardware():
    device = LinuxDeviceAdapter(set(), set())
    command = HardwareMock()
    command.shell_execute()
    assert command.parse()
    assert command.to_axonius('test', device)
    dict_ = device.to_dict()
    del dict_['raw']
    assert dict_ == {'id': 'linux_ssh_test',
                     'device_serial': '9T1MZM2',
                     'device_model': 'XPS 13 9370',
                     'device_model_family': 'XPS',
                     'device_manufacturer': 'Dell Inc.',
                     'motherboard_model': '0F6P3V',
                     'motherboard_version': 'A00',
                     'motherboard_manufacturer': 'Dell Inc.',
                     'cpus': [{'name': 'Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz', 'family': 'Core i7',
                               'cores': 4, 'cores_thread': 8, 'ghz': 3.7, 'manufacturer': 'Intel(R) Corporation'}],
                     'bios_version': '1.6.3',
                     'batteries': [{'model': 'DELL G8VCF6C', 'capacity': '51990 mWh', 'manufacturer': 'SMP'}]}


def test_executor():
    device = LinuxDeviceAdapter(set(), set())
    executor = MockCommandExecutor()
    executor.add_dynamic_command(MD5FilesCommandMock('asdf,qwer'))
    for command in executor.get_commands():
        command.to_axonius('test', device)
    assert device.id == ('linux_ssh_02:42:AC:A5:C0:D1_02:42:ED:5B:69:21_0E:CC:77:' +
                         '6D:25:A4_10:65:30:08:54:A4_1A:1C:C8:02:BA:BA_32:' +
                         '93:C3:39:00:5C_36:94:FC:6A:76:DD_46:24:AF:EF:A1:BE_52:54:00:' +
                         'F7:EB:F0_52:54:00:F7:EB:F0_66:BA:53:5C:F2:EC_9C:B6:D0:89:A2:21_BA:' +
                         'A5:93:72:74:01_BE:36:99:D3:1B:C5_DE:CB:76:46:F1:DA_EE:E6:60:FD:C5:45_ip-10-0-2-26_test')
    assert device.to_dict()['os']['build'] == 'testing'
    assert len(device.to_dict()['md5_files_list']) == 2
