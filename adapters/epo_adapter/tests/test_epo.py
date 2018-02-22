from epo_adapter import service
import pytest

from axonius.devices.device import Device
from axonius.parsing_utils import figure_out_os
from axonius.utils.mongo_escaping import escape_dict
from unittest.mock import MagicMock

list_tables = {
    'columns': '\r\n    Name                         Type          Select? Condition? GroupBy? Order? Number? \r\n    ---------------------------- ------------- ------- ---------- -------- ------ -------\r\n    AutoID                       int           False   False      False    True   True   \r\n    Tags                         string        True    False      False    True   False  \r\n    ExcludedTags                 string        True    False      False    True   False  \r\n    AppliedTags                  applied_tags  False   True       False    False  False  \r\n    LastUpdate                   timestamp     True    True       True     True   False  \r\n    os                           string        True    False      False    False  False  \r\n    products                     string        False   False      False    False  False  \r\n    NodeName                     string        True    True       True     True   False  \r\n    ManagedState                 enum          True    True       False    True   False  \r\n    AgentVersion                 string_lookup True    True       True     True   False  \r\n    AgentGUID                    string        True    False      False    True   False  \r\n    Type                         int           False   False      False    True   False  \r\n    ParentID                     int           False   False      False    True   True   \r\n    ResortEnabled                boolean       True    True       False    True   False  \r\n    ServerKeyHash                string        True    True       False    True   False  \r\n    NodePath                     string_lookup False   False      False    True   False  \r\n    TransferSiteListsID          isNotNull     True    True       False    True   False  \r\n    SequenceErrorCount           int           True    True       False    True   True   \r\n    SequenceErrorCountLastUpdate timestamp     True    True       False    True   False  \r\n    LastCommSecure               string_enum   True    True       True     True   False  \r\n    TenantId                     int           False   False      False    True   True   \r\n',
    'databaseType': '',
    'description': 'Retrieves information about systems that have been added to your System Tree.',
    'foreignKeys': '\r\n    Source table Source Columns Destination table          Destination columns Allows inverse? One-to-one? Many-to-one? \r\n    ------------ -------------- -------------------------- ------------------- --------------- ----------- ------------\r\n    EPOLeafNode  AutoID         EPOComputerProperties      ParentID            False           False       True        \r\n    EPOLeafNode  AutoID         EPOTagAssignment           LeafNodeID          False           False       True        \r\n    EPOLeafNode  ParentID       EPOBranchNode              AutoID              False           False       True        \r\n    EPOLeafNode  AutoID         EPOComputerLdapProperties  LeafNodeId          False           False       True        \r\n    EPOLeafNode  AutoID         EPOProductPropertyProducts ParentID            False           False       True        \r\n',
    'name': 'Managed Systems',
    'relatedTables': '\r\n    Name\r\n    --------------------------\r\n    EPOTagAssignment\r\n    EPOProdPropsView_PCR\r\n    EPOBranchNode\r\n    EPOComputerLdapProperties\r\n    EPOComputerProperties\r\n    EPOProdPropsView_TELEMETRY\r\n    EPOProdPropsView_EPOAGENT\r\n    EPOProductPropertyProducts\r\n',
    'target': 'EPOLeafNode',
    'type': 'target'}

raw_device_data = {'EPOBranchNode.NodeName': 'My Group',
                   'EPOBranchNode.NodeTextPath': 'GlobalRoot\\Directory\\My Group',
                   'EPOBranchNode.NodeTextPath2': '\\My Group\\',
                   'EPOBranchNode.Notes': '',
                   'EPOComputerLdapProperties.LdapOrgUnit': None,
                   'EPOComputerProperties.CPUSerialNum': 'N/A',
                   'EPOComputerProperties.CPUSpeed': 2395,
                   'EPOComputerProperties.CPUType': 'Intel(R) Xeon(R) CPU E5-2676 v3 @ 2.40GHz',
                   'EPOComputerProperties.ComputerName': 'EC2AMAZ-0VJ3RSP',
                   'EPOComputerProperties.DefaultLangID': '0409',
                   'EPOComputerProperties.Description': None,
                   'EPOComputerProperties.DomainName': 'WORKGROUP',
                   'EPOComputerProperties.FreeDiskSpace': 12287,
                   'EPOComputerProperties.FreeMemory': 858911536,
                   'EPOComputerProperties.IPHostName': 'EC2AMAZ-0VJ3RSP.us-east-2.compute.internal',
                   'EPOComputerProperties.IPSubnet': '0:0:0:0:0:FFFF:AC1F:1000',
                   'EPOComputerProperties.IPSubnetMask': '0:0:0:0:0:FFFF:FFFF:F000',
                   'EPOComputerProperties.IPV4x': -1979646028,
                   'EPOComputerProperties.IPV6': '0:0:0:0:0:FFFF:AC1F:154A',
                   'EPOComputerProperties.IPXAddress': 'N/A',
                   'EPOComputerProperties.IsPortable': 0,
                   'EPOComputerProperties.ManagementType': None,
                   'EPOComputerProperties.NetAddress': '06f417360ed8',
                   'EPOComputerProperties.NumOfCPU': 2,
                   'EPOComputerProperties.OSBitMode': 1,
                   'EPOComputerProperties.OSBuildNum': 14393,
                   'EPOComputerProperties.OSOEMID': '00376-40000-00000-AA930',
                   'EPOComputerProperties.OSPlatform': 'Server',
                   'EPOComputerProperties.OSServicePackVer': '',
                   'EPOComputerProperties.OSType': 'Windows 10 Server',
                   'EPOComputerProperties.OSVersion': '10.0',
                   'EPOComputerProperties.SubnetAddress': '',
                   'EPOComputerProperties.SubnetMask': '',
                   'EPOComputerProperties.SystemDescription': 'N/A',
                   'EPOComputerProperties.SysvolFreeSpace': 12287,
                   'EPOComputerProperties.SysvolTotalSpace': 30717,
                   'EPOComputerProperties.TimeZone': 'Coordinated Universal Time',
                   'EPOComputerProperties.TotalDiskSpace': 30717,
                   'EPOComputerProperties.TotalPhysicalMemory': 4294557696,
                   'EPOComputerProperties.UserName': 'administrator',
                   'EPOComputerProperties.UserProperty1': None,
                   'EPOComputerProperties.UserProperty2': None,
                   'EPOComputerProperties.UserProperty3': None,
                   'EPOComputerProperties.UserProperty4': None,
                   'EPOComputerProperties.Vdi': 0,
                   'EPOLeafNode.AgentGUID': 'F982D34B-A2DC-4BD2-AC9A-E2EDA0678899',
                   'EPOLeafNode.AgentVersion': '4.8.0.1938',
                   'EPOLeafNode.ExcludedTags': '',
                   'EPOLeafNode.LastCommSecure': '1',
                   'EPOLeafNode.LastUpdate': '2017-11-02T16:53:07+00:00',
                   'EPOLeafNode.ManagedState': 1,
                   'EPOLeafNode.NodeName': 'EC2AMAZ-0VJ3RSP',
                   'EPOLeafNode.ResortEnabled': False,
                   'EPOLeafNode.SequenceErrorCount': 0,
                   'EPOLeafNode.SequenceErrorCountLastUpdate': None,
                   'EPOLeafNode.ServerKeyHash': 'Cdc8z+SAut5lGDwbV62Ln9YnGHtUM9yjAsA/3TGs0Xk=',
                   'EPOLeafNode.Tags': 'Server',
                   'EPOLeafNode.TransferSiteListsID': False,
                   'EPOLeafNode.os': 'Windows 10 Server|Server|10.0|',
                   'EPOProductPropertyProducts.Products': 'McAfee Agent, Product Improvement Program, PCR_____1000'}


def test_get_all_linked_tables():
    linked_tables = service.get_all_linked_tables(list_tables)
    assert len(linked_tables) > 0
    assert 'EPOComputerProperties' in linked_tables


def test_os():
    details = figure_out_os(raw_device_data.get('EPOLeafNode.os', ''))
    print(details)
    assert details['type'] == 'Windows'
    assert details['distribution'] == '10'


def test_parse_network_positive():
    device = Device(set(), set())
    device.network_interfaces = []
    service.parse_network(raw_device_data, device, MagicMock())
    assert len(device.network_interfaces) == 1
    assert device.network_interfaces[0].mac == "06:f4:17:36:0e:d8".upper()
    assert sorted(device.network_interfaces[0].ips) == sorted(["10.0.255.180", "::ffff:ac1f:154a", "172.31.21.74"])


def test_only_mac():
    raw = {'EPOComputerProperties.NetAddress': '06f417360ed8'}
    device = Device(set(), set())
    device.network_interfaces = []
    service.parse_network(raw, device, MagicMock())
    assert device.network_interfaces[0].mac == "06:f4:17:36:0e:d8".upper()


def test_parse_network_no_ipv6_no_mac():
    raw = {'EPOComputerProperties.IPV4x': -1979646028}
    device = Device(set(), set())
    device.network_interfaces = []
    service.parse_network(raw, device, MagicMock())
    assert device.network_interfaces[0].ips == ['10.0.255.180']


def test_parse_network_no_ipv4_no_mac():
    raw = {'EPOComputerProperties.IPV6': '0:0:0:0:0:FFFF:AC1F:154A'}
    device = Device(set(), set())
    device.network_interfaces = []
    service.parse_network(raw, device, MagicMock())
    assert sorted(device.network_interfaces[0].ips) == sorted(['172.31.21.74', '::ffff:ac1f:154a'])


def test_ip_of_zeroes():
    raw = {'EPOComputerProperties.IPV4x': -2147483648,
           'EPOComputerProperties.IPV6': 'FE80:0:0:0:ECC1:22FF:FED6:AAD4'}
    device = Device(set(), set())
    service.parse_network(raw, device, MagicMock())
    assert sorted(device.network_interfaces[0].ips) == sorted(['fe80::ecc1:22ff:fed6:aad4', '0.0.0.0'])


def test_escape_dict():
    for key in escape_dict(raw_device_data.copy()):
        assert '.' not in key


if __name__ == '__main__':
    pytest.main(["."])
