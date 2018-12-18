from axonius.clients.linux_ssh.mock import (DistroMock, HDMock, HostnameMock,
                                            IfaceMock, VersionMock, MemMock,
                                            DPKGMock, UsersMock)
from axonius.devices.device_adapter import DeviceAdapter


def test_hostname():
    device = DeviceAdapter(set(), set())

    command = HostnameMock('test_hostname')
    assert command.parse()
    assert command.to_axonius(device)

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

    device = DeviceAdapter(set(), set())
    command = IfaceMock('test_iface')
    assert command.parse()
    assert command.to_axonius(device)

    assert list(map(lambda x: x['index'], command._parsed_data)) == indexes

    axon_ifaces = device.to_dict()['network_interfaces']
    assert len(axon_ifaces) == num_of_ifaces
    assert [iface['mtu'] for iface in axon_ifaces] == mtus
    assert [iface['name'] for iface in axon_ifaces] == names
    assert all([iface['mac'] for iface in axon_ifaces if iface['name'] != 'lo'])
    assert all([iface['operational_status'] for iface in axon_ifaces])
    assert len(sum([iface.get('ips', []) for iface in axon_ifaces], [])) == num_of_ipaddresses


def test_hd():
    device = DeviceAdapter(set(), set())
    command = HDMock('test_hd')
    assert command.parse()
    assert command.to_axonius(device)
    assert len(device.to_dict()['hard_drives']) == 9


def test_version_distro():
    device = DeviceAdapter(set(), set())
    command = VersionMock('test_version')
    command2 = DistroMock('test_distro')
    assert command.parse()
    assert command2.parse()
    assert command.to_axonius(device)
    assert command2.to_axonius(device)
    assert device.to_dict()['os']['kernel_version']
    assert device.to_dict()['os']['bitness']
    assert device.to_dict()['os']['distribution']
    assert device.to_dict()['os']['build']


def test_mem():
    device = DeviceAdapter(set(), set())
    command = MemMock('test_mem')
    assert command.parse()
    assert command.to_axonius(device)
    assert device.to_dict()['total_physical_memory'] == 15.39
    assert device.to_dict()['free_physical_memory'] == 7.19
    assert device.to_dict()['physical_memory_percentage'] == 53.27


def test_dpkg():
    device = DeviceAdapter(set(), set())
    command = DPKGMock('test_dpkg')
    assert command.parse()
    assert command.to_axonius(device)
    assert len(device.to_dict()['installed_software']) == 11


def test_users():
    device = DeviceAdapter(set(), set())
    command = UsersMock('test_users')
    assert command.parse()
    assert command.to_axonius(device)
    assert len(device.to_dict()['users']) == 44
    assert len(list(filter(lambda user: user['is_admin'], device.to_dict()['users']))) == 1


def test_raw_data():
    device = DeviceAdapter(set(), set())

    command = HostnameMock('test_hostname')
    assert command.parse()
    command2 = IfaceMock('test_hostname')
    assert command2.parse()
    assert command.to_axonius(device)
    assert command2.to_axonius(device)
    assert [command.NAME, command2.NAME] == list(device.to_dict()['raw'].keys())
