# pylint: disable=redefined-outer-name
from datetime import timedelta

import pytest

from axonius.clients.ldap.ldap_connection import LdapConnection
from axonius.types.ssl_state import SSLState
from axonius.utils.parsing import ad_integer8_to_timedelta
from testing.test_credentials.test_ad_credentials import ad_client1_details

USERNAME = ad_client1_details['user']
PASSWORD = ad_client1_details['password']
ADDRESS = ad_client1_details['dc_name']

ACCOUNTDISABLE = 0x0002


@pytest.fixture(scope='module')
def ldap_connection():
    return LdapConnection(ADDRESS, USERNAME,
                          PASSWORD, None, 900, SSLState[SSLState.Unencrypted.name], bytes([]), bytes([]),
                          bytes([]), True, True)


def test_users_and_full_memberof(ldap_connection: LdapConnection):
    users = list(ldap_connection.get_users_list())

    users_dict = {}
    has_disabled_user = False
    for user in users:
        users_dict[user['sAMAccountName']] = user
        if user['userAccountControl'] & ACCOUNTDISABLE > 0:
            has_disabled_user = True

    assert len(users_dict) > 0
    assert users_dict['avidor']['cn'] == 'Avidor Bartov'
    assert users_dict['Administrator']['adminCount'] == 1
    assert 'maxPwdAge' in users_dict['avidor']['axonius_extended']

    # assert there is at least one disabled device
    assert has_disabled_user is True

    # assert memberof
    groups = ldap_connection.get_nested_groups_for_object(users_dict['avidor'])
    # Currently, Hierarchy is "Avidor" <- "R&D" <- "Circular-Tower" <- "Tel Aviv" <- "Israel"
    # Another hierarchy is "Avidor" <- "AWS Admins" <- "Cloud Team"
    assert any(True if 'Israel' in group else False for group in groups)
    assert any(True if 'Cloud Team' in group else False for group in groups)
    assert not any(True if 'VA Team' in group else False for group in groups)


def test_devices(ldap_connection: LdapConnection):
    devices = ldap_connection.get_device_list()
    devices_dict = {}
    has_disabled_device = True
    for device in devices:
        devices_dict[device['distinguishedName']] = device
        if device['userAccountControl'] & ACCOUNTDISABLE > 0:
            has_disabled_device = True

    assert len(devices_dict) > 0

    test_device = devices_dict['CN=DESKTOP-MPP10U1,CN=Computers,DC=TestDomain,DC=test']
    assert test_device['name'] == 'DESKTOP-MPP10U1'
    assert test_device['operatingSystem'] == 'Windows 10 Pro'

    # assert there is at least one disabled device
    assert has_disabled_device is True


def test_printers(ldap_connection: LdapConnection):
    printers = ldap_connection.get_printers_list()
    printers_dict = {}
    for printer in printers:
        printers_dict[printer['distinguishedName']] = printer

    assert len(printers_dict) > 0

    test_printer = printers_dict['CN=DESKTOP-MPP10U1-AXONIUS-OFFICE-PRINTER (HP Color LaserJet MF,CN=DESKTOP-MPP10U1,'
                                 'CN=Computers,DC=TestDomain,DC=test']
    assert test_printer['serverName'] == 'DESKTOP-MPP10U1.TestDomain.test'


def test_get_fsmo_roles(ldap_connection: LdapConnection):
    fsmo_dict = ldap_connection.get_fsmo_roles()
    assert fsmo_dict['pdc_emulator'] == 'dc1.TestDomain.test'
    assert fsmo_dict['rid_master'] == 'dc1.TestDomain.test'
    assert fsmo_dict['infra_master'] == 'dc1.TestDomain.test'
    assert fsmo_dict['naming_master'] == 'dc1.TestDomain.test'
    assert fsmo_dict['schema_master'] == 'dc1.TestDomain.test'


def test_get_global_catalogs(ldap_connection: LdapConnection):
    global_catalogs = ldap_connection.get_global_catalogs()
    assert 'dc1.TestDomain.test' in global_catalogs
    assert 'raindc1.raindomain.test' in global_catalogs


def test_get_dhcp_servers(ldap_connection: LdapConnection):
    dhcp_servers = ldap_connection.get_dhcp_servers()
    assert 'dc2.testdomain.test' in dhcp_servers


def test_get_domain_properties(ldap_connection: LdapConnection):
    domain_properties = ldap_connection.get_domain_properties()
    assert 'maxPwdAge' in domain_properties
    assert domain_properties['name'] == 'TestDomain'
    assert ad_integer8_to_timedelta(domain_properties['maxPwdAge']) == timedelta(days=999)


def test_get_dc_properties(ldap_connection: LdapConnection):
    dc_properties = ldap_connection.get_dc_properties()
    assert dc_properties['defaultNamingContext'] == ['DC=TestDomain,DC=test']
    assert dc_properties['configurationNamingContext'] == ['CN=Configuration,DC=TestDomain,DC=test']


def test_get_dns_records(ldap_connection: LdapConnection):
    dns_records = list(ldap_connection.get_dns_records())
    assert ('dc', '192.168.20.25') in dns_records
    assert ('DESKTOP-MPP10U1', 'fc3b:db8:85a3:42:1000:8a2e:370:7334') in dns_records

    only_one_dns_record = list(ldap_connection.get_dns_records('dc1'))
    assert len(only_one_dns_record) == 1
    assert ('dc1', '192.168.20.25') in only_one_dns_record


def test_get_sites(ldap_connection: LdapConnection):
    sites = ldap_connection.get_sites()
    sites_dict = {}
    for site in sites:
        sites_dict[site['name']] = site

    assert 'TestDomain-TelAviv' in sites_dict
    assert 'CN=192.168.20.0/24,CN=Subnets,CN=Sites,CN=Configuration,DC=TestDomain,DC=test' in sites_dict[
        'TestDomain-TelAviv']['siteObjectBL']


def test_get_subnets(ldap_connection: LdapConnection):
    subnets = ldap_connection.get_subnets()
    subnets_dict = {}
    for subnet in subnets:
        subnets_dict[subnet['name']] = subnet

    assert '10.0.2.0/24' in subnets_dict
    assert subnets_dict['10.0.2.0/24']['description'] == ['Office Private Subnet']
    assert subnets_dict['10.0.2.0/24']['location'] == 'New York'


def test_get_dfsr_shares(ldap_connection: LdapConnection):
    dfsr_shares_dict = {}
    for dfsr_replication_group_name, dfsr_replication_group_inner in ldap_connection.get_dfsr_shares():
        dfsr_shares_dict[dfsr_replication_group_name] = dfsr_replication_group_inner

    assert 'Tools' in dfsr_shares_dict
    assert 'tools' in dfsr_shares_dict['Tools']['content']
    assert 'CN=WESTDC1,OU=Domain Controllers,DC=west,DC=TestDomain,DC=test' in dfsr_shares_dict['Tools']['servers']


def test_get_extended_devices(ldap_connection: LdapConnection):
    keys = ['devices', 'printers', 'dns_records', 'dfsr_shares',
            'sites', 'dhcp_servers', 'fsmo_roles', 'global_catalogs', 'exchange_servers']

    extended_keys = ldap_connection.get_extended_devices_list().keys()

    assert all([True if key in extended_keys else False for key in keys])


def test_get_exchange_servers(ldap_connection: LdapConnection):
    exchange_servers = ldap_connection.get_exchange_servers()
    exchange_servers = {es['distinguishedName']: es for es in exchange_servers}

    assert 'CN=DC4,CN=Servers,CN=Exchange Administrative Group (FYDIBOHF23SPDLT),CN=Administrative Groups,' \
           'CN=Axonius TestDomain,CN=Microsoft Exchange,CN=Services,' \
           'CN=Configuration,DC=TestDomain,DC=test' in exchange_servers


def test_get_domains_in_forest(ldap_connection: LdapConnection):
    domains_in_forest = {d['nETBIOSName']: d for d in ldap_connection.get_domains_in_forest()}
    assert domains_in_forest['WEST']['name'] == 'WEST'
    assert domains_in_forest['RAINDOMAIN']['msDS-Behavior-Version'] == 7


def test_get_report_statistics(ldap_connection: LdapConnection):
    fs = ldap_connection.get_report_statistics()
    fs = {o['name']: o['data'] for o in fs}
    assert {'group_name': 'Builtin', 'count': 29} in fs['Groups']
    assert {'name': 'Naming Master', 'value': 'dc1.TestDomain.test'} in fs['Forest Summary']
    assert {'name': 'Exchange Version', 'value': '2016'} in fs['Forest Features']
    assert {'name': 'Site Subnet Count', 'value': 8} in fs['Site Summary']
    assert {
        'name': 'TestDomain-Kazakhstan',
        'location': '\u041c\u043e\u0441\u043a\u0432\u0430',
        'domains': '',
        'dcs': '',
        'subnets': ''
    } in fs['Forest Site Summary']
    assert {
        'name': 'TestDomain-NewYork',
        'location': 'New York',
        'domains': 'TestDomain.test',
        'dcs': 'dcny1.TestDomain.test',
        'subnets': '10.0.224.0/20, 10.0.240.0/20, 10.0.3.0/24, 10.0.2.0/24'
    } in fs['Forest Site Summary']
    assert {
        'name': 'TestDomain-TelAviv',
        'options': '',
        'istg': 'raindc1.raindomain.test',
        'site_links': 'TelAviv <-> Kazakhstan, London <-> Tel Aviv, DEFAULTIPSITELINK',
        'bridgehead_servers': 'raindc1.raindomain.test (IP), dc2.TestDomain.test (IP)',
        'adjacent_sites': 'TestDomain-Kazakhstan, TestDomain-London, TestDomain-NewYork'
    }
    assert {'name': '10.0.2.0/24', 'site': 'TestDomain-NewYork', 'location': 'New York'} in fs['Site Subnets']
    assert len(fs['Site Connections']) > 5
    assert {
        'name': 'New York <-> London',
        'repl_interval': '180',
        'cost': '100',
        'type': 'IP',
        'sitelist': 'TestDomain-London, TestDomain-NewYork',
        'change_notification_enabled': True
    } in fs['Site Links']
    assert {
        'name': 'west.TestDomain.test',
        'netbios_name': 'WEST',
        'function_level': 'Windows 2012 R2',
        'forest_root': False,
        'rids_issued': '',
        'rids_remaning': ''
    }
    assert {
        'domain_name': 'TestDomain.test',
        'domain_netbios_name': 'TESTDOMAIN',
        'lockout_threshold': 5,
        'pwd_history_length': 24,
        'max_password_age': '999 days, 0:00:00',
        'min_password_age': '1 day, 0:00:00',
        'min_password_length': 7
    } in fs['Domain Password Policies']
    assert fs['Domain Trusts'][0]['domain'] == 'TestDomain.test'
    assert fs['Domain Trusts'][0]['direction'] == 'Two-Way'
    assert 'Domain Integrated DNS Zones' in fs
    assert 'Domain GPOs' in fs


def test_reconnect_after_disconnection(ldap_connection: LdapConnection):
    ldap_connection.disconnect()
    # Notice! An exception message (logger.exception) is expected to be printed to the screen here.
    test_devices(ldap_connection)
