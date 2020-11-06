# pylint: disable=too-many-lines
import logging
from collections import defaultdict
from itertools import combinations

from axonius.blacklists import ALL_BLACKLIST, FROM_FIELDS_BLACK_LIST_REG, compare_reg_mac
from axonius.consts.plugin_consts import PLUGIN_NAME, ACTIVE_DIRECTORY_PLUGIN_NAME
from axonius.correlator_base import (has_ad_or_azure_name, has_cloud_id,
                                     has_hostname, has_last_used_users, has_public_ips,
                                     has_mac, has_name, has_serial, has_nessus_scan_no_id, has_resource_id)
from axonius.correlator_engine_base import (CorrelatorEngineBase, CorrelationMarker)
from axonius.plugin_base import PluginBase
from axonius.types.correlation import CorrelationReason
from axonius.utils.parsing import (NORMALIZED_MACS,
                                   asset_hostnames_do_not_contradict,
                                   compare_ad_name_or_azure_display_name,
                                   compare_asset_hosts, compare_asset_name,
                                   compare_bios_serial_serial, compare_clouds,
                                   compare_device_normalized_hostname,
                                   compare_hostname, is_valid_ip,
                                   compare_last_used_users,
                                   get_ad_name_or_azure_display_name,
                                   get_asset_name, get_asset_or_host, get_manufacturer_from_mac,
                                   get_asset_snow_or_host, compare_snow_asset_hosts, is_asset_before_host_device,
                                   get_bios_serial_or_serial, get_cloud_data,
                                   get_hostname, compare_full_mac,
                                   get_last_used_users, is_from_ad,
                                   get_normalized_hostname_str, is_snow_adapter,
                                   get_normalized_ip, get_serial, get_os_type,
                                   hostnames_do_not_contradict,
                                   ips_do_not_contradict_or_mac_intersection, macs_do_not_contradict,
                                   is_azuread_or_ad_and_have_name,
                                   hostname_not_problematic, os_do_not_contradict,
                                   is_different_plugin, ips_do_not_contradict,
                                   is_from_juniper_and_asset_name,
                                   is_windows, is_linux, get_cloud_id_or_hostname, compare_cloud_id_or_hostname,
                                   is_junos_space_device,
                                   is_old_device, is_sccm_or_ad,
                                   is_splunk_vpn, normalize_adapter_devices,
                                   serials_do_not_contradict, compare_macs_or_one_is_jamf,
                                   not_wifi_adapters, not_wifi_adapter,
                                   cloud_id_do_not_contradict,
                                   get_serial_no_s, compare_serial_no_s,
                                   get_bios_serial_or_serial_no_s, compare_bios_serial_serial_no_s,
                                   get_hostname_or_serial, compare_hostname_serial,
                                   is_from_deeps_tenable_io_or_aws, get_nessus_no_scan_id,
                                   compare_nessus_no_scan_id,
                                   is_domain_valid, compare_uuid, get_uuid,
                                   get_azure_ad_id, compare_azure_ad_id, get_hostname_no_localhost, get_dns_names)

# pylint: disable=too-many-branches, too-many-statements

logger = logging.getLogger(f'axonius.{__name__}')

USERS_CORRELATION_ADAPTERS = ['illusive_adapter', 'carbonblack_protection_adapter', 'quest_kace_adapter']
ALLOW_OLD_MAC_LIST = ['clearpass_adapter', 'tenable_security_center', 'nexpose_adapter', 'nessus_adapter',
                      'nessus_csv_adapter', 'tenable_io_adapter', 'qualys_scans_adapter', 'airwave_adapter',
                      'counter_act_adapter', 'tanium_discover_adapter', 'infoblox_adapter', 'aws_adapter',
                      'airwatch_adapter', 'iboss_cloud_adapter']
DANGEROUS_ADAPTERS = ['lansweeper_adapter', 'carbonblack_protection_adapter', 'counter_act_adapter', 'nexpose_adapter',
                      'infoblox_adapter', 'azure_ad_adapter', 'tanium_discover_adapter', 'qualys_scans_adapter',
                      'solarwinds_orion_adapter', 'mssql_adapter', 'iboss_cloud_adapter']
SEMI_DANGEROUS_ADAPTERS = ['symantec_adapter', 'tanium_asset_adapter']
DOMAIN_TO_DNS_DICT = dict()
DOES_AD_HAVE_ONE_CLIENT = False
ALLOW_SERVICE_NOW_BY_NAME_ONLY = False
DUPLICATES_SERIALS_IGAR = []


def get_private_dns_name(adapter_device):
    return adapter_device['data'].get('private_dns_name')


def is_palolato_vpn(adapter_device):
    if not adapter_device.get('plugin_name') == 'paloalto_panorama_adapter':
        return False
    return adapter_device['data'].get('paloalto_device_type') == 'VPN Device'


def is_only_host_adapter(adapter_device):
    if adapter_device.get('plugin_name') == 'csv_adapter' \
            and '/Microsoft.Compute/' in (adapter_device['data'].get('id') or ''):
        return False
    if (adapter_device.get('plugin_name') in ['deep_security_adapter',
                                              'cisco_umbrella_adapter',
                                              'bitlocker_adapter',
                                              'carbonblack_defense_adapter',
                                              'carbonblack_protection_adapter',
                                              'csv_adapter',
                                              'mssql_adapter',
                                              'code42_adapter',
                                              'avamar_adapter',
                                              'cherwell_adapter',
                                              'signalsciences_adapter',
                                              'sysaid_adapter',
                                              'logrhythm_adapter',
                                              'pkware_adapter',
                                              'splunk_adapter',
                                              'cloud_health_adapter',
                                              'symantec_ee_adapter',
                                              'arsenal_adapter',
                                              'guardium_adapter',
                                              'datadog_adapter',
                                              'observium_adapter',
                                              'ansible_tower_adapter',
                                              'cisco_ucm_adapter',
                                              'symantec_dlp_adapter',
                                              'netskope_adapter',
                                              'sumo_logic_adapter',
                                              'bigid_adapter',
                                              'json_adapter',
                                              'epo_adapter',
                                              'observeit_adapter',
                                              'crowd_strike_adapter',
                                              'amd_db_adapter',
                                              'hp_nnmi_adapter',
                                              'sal_adapter',
                                              'snipeit_adapter',
                                              'checkmarx_adapter',
                                              'iboss_cloud_adapter',
                                              'druva_adapter',
                                              'itop_adapter',
                                              'uptycs_adapter',
                                              'ibm_qradar_adapter']):
        return True
    try:
        if adapter_device.get('plugin_name') == 'active_directory_adapter' and \
                (DOES_AD_HAVE_ONE_CLIENT or 'OU=Linux,' in adapter_device['data'].get('id')
                 or is_linux(adapter_device)):
            return True
    except Exception:
        pass
    if (adapter_device.get('plugin_name').lower() == 'cisco_prime_adapter' and
            adapter_device['data'].get('fetch_proto') == 'CDP'):
        return True
    if adapter_device.get('plugin_name') in ['flexera_adapter'] and not get_domain_for_correlation(adapter_device):
        return True
    return False


def is_cherwell_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'cherwell_adapter'


def is_zscaler_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'zscaler_adapter'


def is_deep_security_device(adapter_device):
    return adapter_device.get('plugin_name') == 'deep_security_adapter'


def is_bomgar_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'bomgar_adapter'


def is_only_host_adapter_or_host_only_force(adapter_device):
    return (is_only_host_adapter(adapter_device) and
            (not adapter_device.get(NORMALIZED_MACS) and not get_normalized_ip(adapter_device))) \
        or is_palolato_vpn(adapter_device) or is_cherwell_adapter(adapter_device) \
        or is_zscaler_adapter(adapter_device) or is_bomgar_adapter(adapter_device)\
        or is_service_now_and_no_other(adapter_device) or is_deep_security_device(adapter_device) \
        or is_force_hostname_when_no_mac_device(adapter_device)


def is_only_host_adapter_not_localhost(adapter_device):
    return is_only_host_adapter(adapter_device) and hostname_not_problematic(adapter_device)


def get_fqdn(adapter_device):
    # For now we support only Chef to avoid confusion of future adapters writers
    if adapter_device.get('plugin_name') not in ['chef_adapter']:
        return None
    return adapter_device['data'].get('fqdn')


def get_fqdn_or_hostname(adapter_device):
    fqdn_hostname = get_fqdn(adapter_device) or get_normalized_hostname_str(adapter_device)
    if fqdn_hostname:
        return fqdn_hostname.split('.')[0].lower()
    return None


def get_resource_id(adapter_device):
    return adapter_device['data'].get('resource_id')


def get_one_public_ip(adapter_device):
    public_ips = adapter_device['data'].get('public_ips')
    if not public_ips:
        return None
    if len(public_ips) == 1:
        return public_ips[0]
    return None


def compare_one_public_ip(adapter_device1, adapter_device2):
    if not get_one_public_ip(adapter_device1) or not get_one_public_ip(adapter_device2):
        return False
    return get_one_public_ip(adapter_device1) == get_one_public_ip(adapter_device2)


def is_public_ip_correlation_adapter(adapter_device):
    return adapter_device.get('plugin_name') in ['edfs_csv_adapter',
                                                 'aws_adapter',
                                                 'gce_adapter',
                                                 'dns_made_easy_adapter',
                                                 'azure_adapter',
                                                 'nmap_adapter',
                                                 'digital_shadows_adapter',
                                                 'masscan_adapter',
                                                 'shodan_adapter',
                                                 'bitsight_adapter',
                                                 'censys_adapter',
                                                 'cycognito_adapter',
                                                 'panorays_adapter',
                                                 'riskiq_adapter',
                                                 'riskiq_csv_adapter']


def get_dst_name(adapter_device):
    return adapter_device['data'].get('ad_distinguished_name')


def compare_dst_name(adapter_device1, adapter_device2):
    if not get_dst_name(adapter_device1) or not get_dst_name(adapter_device2):
        return False
    return get_dst_name(adapter_device1) == get_dst_name(adapter_device2)


def get_agent_uuid(adapter_device):
    if adapter_device.get('plugin_name') not in ['tenable_io_adapter', 'tenable_security_center_adapter']:
        return None
    agent_uuid = adapter_device['data'].get('agent_uuid') or adapter_device['data'].get('uuid')
    if agent_uuid:
        return agent_uuid.replace('-', '').lower()
    return None


def get_customer(adapter_device):
    if not adapter_device.get('plugin_name') == 'chef_adapter':
        return None
    return adapter_device['data'].get('customer')


def hostnames_do_not_contradict_or_tenable_io(adapter_device1, adapter_device2):
    # pylint: disable=line-too-long
    if hostnames_do_not_contradict(adapter_device1, adapter_device2):
        return True
    if adapter_device1.get('plugin_name') == 'tenable_io_adapter' and \
            adapter_device2.get('plugin_name') == 'tenable_io_adapter':
        if get_hostname(adapter_device1) == 'MacBook-Pro.local' or get_hostname(adapter_device2) == 'MacBook-Pro.local':
            return True
    return False


def compare_agent_uuids(adapter_device1, adapter_device2):
    if not get_agent_uuid(adapter_device1) or not get_agent_uuid(adapter_device2):
        return False
    return get_agent_uuid(adapter_device1) == get_agent_uuid(adapter_device2)


def agent_uuid_do_not_contradict(adapter_device1, adapter_device2):
    if not get_agent_uuid(adapter_device1) or not get_agent_uuid(adapter_device2):
        return True
    return get_agent_uuid(adapter_device1) == get_agent_uuid(adapter_device2)


def customer_do_not_contradict(adapter_device1, adapter_device2):
    if not get_customer(adapter_device1) or not get_customer(adapter_device2):
        return True
    return get_customer(adapter_device1) == get_customer(adapter_device2)


def get_asset_or_host_full(adapter_device):
    asset = get_asset_name(adapter_device) or get_hostname(adapter_device)
    if asset:
        return asset.lower().strip()
    return None


def compare_asset_hosts_full(adapter_device1, adapter_device2):
    asset1 = get_asset_or_host_full(adapter_device1)
    asset2 = get_asset_or_host_full(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_host_or_asset_full(adapter_device):
    asset = get_hostname(adapter_device) or get_asset_name(adapter_device)
    if asset:
        return asset.lower().strip()
    return None


def compare_hosts_asset_full(adapter_device1, adapter_device2):
    asset1 = get_host_or_asset_full(adapter_device1)
    asset2 = get_host_or_asset_full(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_sccm_server(adapter_device):
    return adapter_device['data'].get('sccm_server')


def compare_resource_id(adapter_device1, adapter_device2):
    if not get_resource_id(adapter_device1) or not get_resource_id(adapter_device2):
        return False
    return get_resource_id(adapter_device1) == get_resource_id(adapter_device2)


def compare_sccm_server(adapter_device1, adapter_device2):
    if not get_sccm_server(adapter_device1) or not get_sccm_server(adapter_device2):
        return False
    return get_sccm_server(adapter_device1) == get_sccm_server(adapter_device2)


def compare_fqdn_or_hostname(adapter_device1, adapter_device2):
    if not get_fqdn_or_hostname(adapter_device1) or not get_fqdn_or_hostname(adapter_device2):
        return False
    return get_fqdn_or_hostname(adapter_device1) == get_fqdn_or_hostname(adapter_device2)


def get_email(adapter_device):
    return adapter_device['data'].get('email')


def compare_emails(adapter_device1, adapter_device2):
    email1 = get_email(adapter_device1)
    email2 = get_email(adapter_device2)
    if not email1 or not email2:
        return False
    return email1.lower() == email2.lower()


def get_prefix_private_dns_or_hostname(adapter_device):
    private_dns = get_private_dns_name(adapter_device)
    if private_dns:
        private_dns = private_dns.lower()
        return private_dns.split('.')[0]
    hostname = get_hostname(adapter_device)
    if hostname:
        hostname = hostname.lower()
        return hostname.split('.')[0]
    return None


def is_netbox_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'netbox_adapter'


def is_from_twistlock(adapter_device):
    return adapter_device.get('plugin_name') == 'twistlock_adapter'


def is_from_digicert_pki(adapter_device):
    return adapter_device.get('plugin_name') == 'digicert_pki_platform_adapter'


def is_claroty_ten_adapter_more_mac(adapter_device):
    if adapter_device.get('plugin_name') not in ['claroty_adapter', 'tenable_io_adapter', 'opswat_adapter',
                                                 'office_scan_adapter']:
        return False
    macs = adapter_device.get(NORMALIZED_MACS)
    if macs and len(macs) > 1:
        return True
    return False


def is_esx_and_hostname_more_mac(adapter_device):
    if adapter_device.get('plugin_name') not in ['esx_adapter']:
        return False
    macs = adapter_device.get(NORMALIZED_MACS)
    if macs and len(macs) > 1 and get_hostname(adapter_device):
        return True
    return False


def get_solarwinds_ip_or_hostname(adapter_device):
    return adapter_device['data'].get('solarwinds_ip') or adapter_device['data'].get('hostname')


def compare_solarwinds_ip_or_hostname(adapter_device1, adapter_device2):
    solarwinds_ip_1 = get_solarwinds_ip_or_hostname(adapter_device1)
    solarwinds_ip_2 = get_solarwinds_ip_or_hostname(adapter_device2)
    if not solarwinds_ip_1 or not solarwinds_ip_2:
        return False
    return solarwinds_ip_1 == solarwinds_ip_2


def is_ca_cmdb_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'ca_cmdb_adapter'


def is_ivanti_cm_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'ivanti_sm_adapter'


def is_service_now_and_no_other(adapter_device):
    if not is_snow_adapter(adapter_device):
        return False
    try:
        if ALLOW_SERVICE_NOW_BY_NAME_ONLY:
            return True
    except Exception:
        pass
    if not get_hostname(adapter_device) \
            and not get_normalized_ip(adapter_device) \
            and not get_serial(adapter_device) and not adapter_device.get(NORMALIZED_MACS):
        return True
    return False


def is_only_asset_nams_adapter(adapter_device):
    name = get_asset_name(adapter_device) or ''
    return is_ca_cmdb_adapter(adapter_device) or \
        (is_netbox_adapter(adapter_device) and not get_normalized_ip(adapter_device) and '.' not in name) \
        or is_ivanti_cm_adapter(adapter_device) or is_service_now_and_no_other(adapter_device)


def is_csv_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'csv_adapter'


def is_chef_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'chef_adapter'


def is_aws_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'aws_adapter'


def is_azure_ad_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'azure_ad_adapter'


def is_aws_or_chef_adapter(adapter_device):
    return is_chef_adapter(adapter_device) or is_aws_adapter(adapter_device)


def is_asset_ok_hostname_no_adapters(adapter_device):
    if is_service_now_and_no_other(adapter_device):
        return True
    return adapter_device.get('plugin_name') in ['aws_adapter', 'chef_adapter', 'jamf_adapter', 'iboss_cloud_adapter',
                                                 'epo_adapter', 'esx_adapter', 'active_directory_adapter']


def if_csv_compare_full_path(adapter_device1, adapter_device2):
    # if not is_csv_adapter(adapter_device1) and not is_csv_adapter(adapter_device2):
    #     return True
    hostname1 = adapter_device1['data'].get('hostname')
    hostname2 = adapter_device2['data'].get('hostname')
    if not hostname1 or not hostname2:
        return False
    return hostname1.lower().startswith(hostname2.lower()) or hostname2.lower().startswith(hostname1.lower())


def asset_hostnames_do_not_contradict_and_no_chef(adapter_device1, adapter_device2):
    return asset_hostnames_do_not_contradict(adapter_device1, adapter_device2) \
        or is_asset_ok_hostname_no_adapters(adapter_device1) or is_asset_ok_hostname_no_adapters(adapter_device2)


# pylint: disable=invalid-name
def ips_do_not_contradict_or_mac_intersection_or_asset_only_adapter(adapter_device1, adapter_device2):
    return ips_do_not_contradict_or_mac_intersection(adapter_device1, adapter_device2) \
        or is_only_asset_nams_adapter(adapter_device1) or is_only_asset_nams_adapter(adapter_device2)


def not_mobile(adapter_device):
    os_type = get_os_type(adapter_device)
    if not os_type:
        return True
    return os_type.lower() not in ['android', 'ios']


def is_azure_ad_adapter_not_mobile(adapter_device):
    return is_azure_ad_adapter(adapter_device) and not_mobile(adapter_device)


def ips_do_not_contradict_or_mac_intersection_or_asset_only_adapter_and_azure_ad(adapter_device1, adapter_device2):
    return ips_do_not_contradict_or_mac_intersection_or_asset_only_adapter(adapter_device1, adapter_device2) \
        or is_azure_ad_adapter_not_mobile(adapter_device1) or is_azure_ad_adapter_not_mobile(adapter_device2)
# pylint: enable=invalid-name


def compare_hostname_or_private_dns(adapter_device1, adapter_device2):
    private_dns_or_hostname1 = get_prefix_private_dns_or_hostname(adapter_device1)
    private_dns_or_hostname2 = get_prefix_private_dns_or_hostname(adapter_device2)
    if not private_dns_or_hostname1 or not private_dns_or_hostname2:
        return False
    return private_dns_or_hostname1 == private_dns_or_hostname2


def is_from_twistlock_or_cloud(adapter_device):
    return (adapter_device.get('plugin_name') == 'aws_adapter' and
            adapter_device['data'].get('aws_device_type') == 'EC2') or \
        adapter_device.get('plugin_name') == 'twistlock_adapter' or \
        (adapter_device.get('plugin_name') == 'gce_adapter' and adapter_device['data'].get('device_type') == 'COMPUTE')


def is_airwatch_adapter(adapter_device):
    return adapter_device.get('plugin_name') == 'airwatch_adapter'


def one_is_ad_one_is_airwatch(adapter_device1, adapter_device2):
    return (is_from_ad(adapter_device1) and is_airwatch_adapter(adapter_device2)) \
        or (is_from_ad(adapter_device2) and is_airwatch_adapter(adapter_device1))


def friendly_name_or_ad_name(adapter_device):
    if is_airwatch_adapter(adapter_device):
        if adapter_device['data'].get('friendly_name') and ' ' not in adapter_device['data'].get('friendly_name'):
            return adapter_device['data'].get('friendly_name').lower()[:15]
    if is_from_ad(adapter_device) and get_hostname(adapter_device):
        return get_hostname(adapter_device).split('.')[0].lower()
    return None


def compare_friendly_ad_name(adapter_device1, adapter_device2):
    friendly1 = friendly_name_or_ad_name(adapter_device1)
    friendly2 = friendly_name_or_ad_name(adapter_device2)
    if not friendly1 or not friendly2:
        return False
    return friendly1 == friendly2


def is_force_hostname_when_no_mac_device(adapter_device):
    if adapter_device.get('plugin_name') in ['carbonblack_defense_adapter'] and not adapter_device.get(NORMALIZED_MACS):
        return True
    return False


def cb_defense_basic_id_condradict(adapter_device1, adapter_device2):
    if adapter_device1.get('plugin_name') not in ['carbonblack_defense_adapter'] \
            or adapter_device2.get('plugin_name') not in ['carbonblack_defense_adapter']:
        return False
    basic_device_id_1 = adapter_device1['data'].get('basic_device_id')
    basic_device_id_2 = adapter_device2['data'].get('basic_device_id')
    if not basic_device_id_1 or not basic_device_id_2:
        return False
    if basic_device_id_1 != basic_device_id_2:
        return False
    if hostnames_do_not_contradict(adapter_device1, adapter_device2):
        return False
    return True


def force_mac_adapters(adapter_device):
    return adapter_device.get('plugin_name') in ['sentinelone_adapter', 'carbonblack_defense_adapter', 'aws_adapter',
                                                 'nexpose_adapter']

# pylint: disable=global-statement


def get_asset_gce_chef(adapter_device):
    name = adapter_device['data'].get('name')
    if not name:
        return None
    name = name.lower()
    if adapter_device.get('plugin_name') == 'chef_adapter':
        if '.' not in name:
            return None
        return name.split('.')[0] + '-' + name.split('.')[1]
    if adapter_device.get('plugin_name') == 'gce_adapter':
        return name
    return None


def compare_asset_gce_chef(adapter_device1, adapter_device2):
    asset1 = get_asset_gce_chef(adapter_device1)
    asset2 = get_asset_gce_chef(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_fw_ip(adapter_device):
    return adapter_device['data'].get('fw_ip')


def comapre_fw_ip(adapter_device1, adapter_device2):
    asset1 = get_fw_ip(adapter_device1)
    asset2 = get_fw_ip(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def is_a_record_device(adapter_device):
    return adapter_device.get('plugin_name') == 'infoblox_adapter' \
        and adapter_device['data'].get('fetch_type') == 'A Record'


def is_full_hostname_adapter(adapter_device):
    return adapter_device.get('plugin_name') in ['active_directory_adapter', 'panorays_adapter',
                                                 'sccm_adapter', 'cisco_firepower_management_center_adapter'] \
        or is_a_record_device(adapter_device) or (hostname_not_problematic(adapter_device)
                                                  and adapter_device.get('plugin_name') in ['tanium_adapter',
                                                                                            'free_ipa_adapter'])


# Solarwinds Node are bad for MAC correlation
def not_solarwinds_node(adapter_device):
    if adapter_device.get('plugin_name') == 'solarwinds_orion_adapter' \
            and adapter_device['data'].get('device_type') == 'Node Device':
        return False
    return True


def is_solarwinds_node_or_junos_basic(adapter_device):
    if adapter_device.get('plugin_name') in ['solarwinds_orion_adapter', 'junos_adapter'] \
            and adapter_device['data'].get('device_type') in ['Juniper Device', 'Node Device']:
        return True
    return False


def if_soalrwinds_compare_all(adapter_device1, adapter_device2):
    if not_solarwinds_node(adapter_device1) and not_solarwinds_node(adapter_device2):
        return True
    return compare_full_mac(adapter_device1, adapter_device2)


def not_saltstack_enterprise_linux(adapter_device):
    if adapter_device.get('plugin_name') == 'saltstack_enterprise_adapter' \
            and is_linux(adapter_device):
        return False
    return True


def is_uuid_adapters(adapter_device):
    if adapter_device.get('plugin_name') in ['tanium_sq_adapter', 'tanium_adapter']:
        return True
    if adapter_device.get('plugin_name') == 'sentinelone_adapter' and get_os_type(adapter_device) == 'OS X':
        return True
    return False


def get_normalized_ip_or_is_asset_only(adapter_device):
    return get_normalized_ip(adapter_device) or is_only_asset_nams_adapter(adapter_device)


def not_lansweeper_assetname_no_hostname(adapter_device):
    if adapter_device.get('plugin_name') == 'lansweeper_adapter' \
            and adapter_device['data'].get('name')\
            and not adapter_device['data'].get('hostname'):
        return False
    return True


def _refresh_domain_to_dns_dict():
    try:
        global DOMAIN_TO_DNS_DICT
        DOMAIN_TO_DNS_DICT = PluginBase.Instance.get_global_keyval('ldap_nbns_to_dns') or {}
    except Exception:
        logger.exception(f'Warning - could not refresh domain dns dict')


# pylint: disable=protected-access
def _refresh_ad_client_count():
    global DOES_AD_HAVE_ONE_CLIENT
    try:
        clients_count = 0
        for doc in PluginBase.Instance.core_configs_collection.find({'plugin_name': 'active_directory_adapter'}):
            if not doc.get('plugin_unique_name'):
                continue
            clients_count += PluginBase.Instance._get_collection(
                'clients', db_name=doc['plugin_unique_name']).find({}).count()

        logger.info(f'Active directory clients count: {clients_count}')
        DOES_AD_HAVE_ONE_CLIENT = clients_count == 1
    except Exception:
        logger.exception(f'Warning - could not refresh AD client count. setting to false')
        DOES_AD_HAVE_ONE_CLIENT = False


def get_domain_for_correlation(adapter_device):
    domain = adapter_device['data'].get('domain')
    if domain and is_domain_valid(domain):
        try:
            domain_dns_name = DOMAIN_TO_DNS_DICT.get(domain.lower())
            if domain_dns_name:
                return domain_dns_name.upper()
        except Exception:
            pass
        return domain.upper()
    return None


def domain_do_not_contradict(adapter_device1, adapter_device2):
    domain1 = get_domain_for_correlation(adapter_device1)
    domain2 = get_domain_for_correlation(adapter_device2)
    if not domain1 or not domain2:
        return True
    return domain1 in domain2 or domain2 in domain1


def compare_domain_for_correlation(adapter_device1, adapter_device2):
    domain1 = get_domain_for_correlation(adapter_device1)
    domain2 = get_domain_for_correlation(adapter_device2)
    if domain1 and domain2:
        if domain1 in domain2 or domain2 in domain1:
            return True
    return False


def is_snow_netgear_adapter(adapter_device):
    if not is_snow_netgear_adapter(adapter_device):
        return False
    return adapter_device['data'].get('table_type') == 'Network Device'


def get_asset_or_host_no_dash(adapter_device):
    asset = get_asset_name(adapter_device) or get_hostname(adapter_device)
    if asset:
        asset = asset.strip()
        if is_valid_ip(asset) or ' ' in asset:
            return asset
        return asset.split('.')[0].lower().strip().split('-')[0]
    return None


def compare_asset_hosts_no_dash(adapter_device1, adapter_device2):
    asset1 = get_asset_or_host_no_dash(adapter_device1)
    asset2 = get_asset_or_host_no_dash(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_imei(adapter_device):
    if adapter_device.get('plugin_name') not in ['mobileiron_adapter']:
        return None
    imei = adapter_device['data'].get('imei')
    if not imei:
        return None
    return imei.lower().replace(' ', '')


def get_imei_or_serial(adapter_device):
    if get_imei(adapter_device):
        return get_imei(adapter_device)
    if adapter_device.get('plugin_name') not in ['service_now_adapter', 'service_now_sql_adapter',
                                                 'service_now_akana_adapter']:
        return None
    return get_serial(adapter_device)


def compare_imei_or_serial(adapter_device1, adapter_device2):
    asset1 = get_imei_or_serial(adapter_device1)
    asset2 = get_imei_or_serial(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_host_or_asset_no_dash(adapter_device):
    asset = get_hostname(adapter_device) or get_asset_name(adapter_device)
    if asset:
        asset = asset.strip()
        if is_valid_ip(asset) or ' ' in asset:
            return asset
        return asset.split('.')[0].lower().strip().split('-')[0]
    return None


def compare_host_or_asset_no_dash(adapter_device1, adapter_device2):
    asset1 = get_host_or_asset_no_dash(adapter_device1)
    asset2 = get_host_or_asset_no_dash(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_host_serial_g(adapter_device):
    if is_snow_adapter(adapter_device):
        asset = get_serial(adapter_device)
        if not asset or not asset.strip():
            return None
        return asset.strip().lower()
    asset = get_hostname(adapter_device)
    if not asset or not asset.strip():
        return None
    asset = asset.strip().lower().split('.')[0]
    if not asset.startswith('g') or not asset.endswith('e'):
        return None
    asset = asset[1:-1]
    if not asset:
        return None
    return asset


def compare_host_serial_g(adapter_device1, adapter_device2):
    asset1 = get_host_serial_g(adapter_device1)
    asset2 = get_host_serial_g(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def one_is_not_snow(adapter_device1, adapter_device2):
    if is_snow_adapter(adapter_device1) and is_snow_adapter(adapter_device2):
        return False
    return True


# pylint:disable=too-many-return-statements
def get_v_dash_name(adapter_device):
    if is_snow_adapter(adapter_device):
        asset = get_asset_name(adapter_device)
        if not asset or not asset.strip():
            return None
        return asset.lower()
    if adapter_device.get('plugin_name') not in ['qualys_scans_adapter', 'tanium_discover_adapter']:
        return None
    if not get_hostname(adapter_device):
        return None
    asset = get_hostname(adapter_device)
    asset = asset.split('.')[0].strip().lower()
    if '-' not in asset:
        return None
    last_part = asset.split('-')[-1]
    good_last_part = False
    if last_part == 'mgt_ip':
        good_last_part = True
    if last_part.startswith('v') or last_part.startswith('l'):
        last_int = last_part[1:]
        try:
            int(last_int)
            good_last_part = True
        except Exception:
            pass
    if not good_last_part:
        return None
    asset = '-'.join(asset.split('-')[:-1])
    return asset


def compare_v_dash_name(adapter_device1, adapter_device2):
    asset1 = get_v_dash_name(adapter_device1)
    asset2 = get_v_dash_name(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def igar_with_no_serial(adapter_device):
    if not adapter_device.get('plugin_name') in ['igar_adapter']:
        return True
    if not get_hostname(adapter_device):
        return True
    comments = adapter_device['data'].get('comments')
    if comments and '/virtualMachines/' in comments:
        return False
    hostname = get_hostname(adapter_device).split('.')[0].lower()
    return hostname not in DUPLICATES_SERIALS_IGAR


def remove_qualys_no_mac_with_cloud_id(adapter_device):
    if not adapter_device.get('plugin_name') in ['qualys_scans_adapter']:
        return True
    if not get_cloud_data(adapter_device):
        return True
    if adapter_device.get(NORMALIZED_MACS):
        return True
    return False


def get_host_asset_azure_ad(adapter_device):
    asset = get_asset_or_host_full(adapter_device)
    if asset:
        return asset.split('.')[0].strip('$')
    return None


def host_asset_azure_ad_do_not_contradict(adapter_device1, adapter_device2):
    asset1 = get_host_asset_azure_ad(adapter_device1)
    asset2 = get_host_asset_azure_ad(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_alias_name(adapter_device):
    if is_snow_adapter(adapter_device):
        asset = adapter_device['data'].get('u_alias')
        if not asset or not asset.strip():
            return None
        return asset.strip().lower()
    if adapter_device.get('plugin_name') not in ['ca_spectrum_adapter', 'netbrain_adapter']:
        return None
    asset = get_hostname(adapter_device)
    if not asset or not asset.strip():
        return None
    return asset.strip().lower()


def compare_alias_name(adapter_device1, adapter_device2):
    asset1 = get_alias_name(adapter_device1)
    asset2 = get_alias_name(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_cp_esx_csv(adapter_device):
    if adapter_device.get('plugin_name') not in ['csv_adapter', 'esx_adapter']:
        return None
    asset = get_asset_name(adapter_device)
    if not asset:
        return None
    asset = asset.upper()
    if adapter_device.get('plugin_name') == 'esx_adapter':
        if '-' not in asset:
            return None
        last_dash = asset.split('-')[-1]
        if last_dash in ['QQQ', '2000']:
            asset = '-'.join(asset.split('-')[:-1])
        last_dash = asset.split('-')[-1]
        try:
            float(last_dash)
        except Exception:
            return asset
        if len(asset.split('-')) < 2:
            return None
        if asset.split('-')[-2] not in ['QQQ', '2000']:
            return '-'.join(asset.split('-')[:-1])
        if len(asset.split('-')) < 3:
            return None
        return '-'.join(asset.split('-')[:-2])
    if adapter_device.get('plugin_name') == 'csv_adapter':
        if adapter_device['data'].get('file_name') != 'profiles_db':
            return None
        if get_asset_name(adapter_device) != get_hostname(adapter_device):
            return None
        if get_serial(adapter_device) or adapter_device.get(NORMALIZED_MACS):
            return None
        return asset
    return None


def compare_cp_esx_csv(adapter_device1, adapter_device2):
    asset1 = get_cp_esx_csv(adapter_device1)
    asset2 = get_cp_esx_csv(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def get_ec2_id_route53(adapter_device):
    if not adapter_device.get('plugin_name') == 'aws_adapter':
        return None
    if adapter_device['data'].get('aws_device_type') == 'EC2':
        return adapter_device['data'].get('id')
    return adapter_device['data'].get('route53_ec2_instance_id')


def compare_ec2_id_route53(adapter_device1, adapter_device2):
    asset1 = get_ec2_id_route53(adapter_device1)
    asset2 = get_ec2_id_route53(adapter_device2)
    if asset1 and asset2 and asset1 == asset2:
        return True
    return False


def esx_and_csv(adapter_device1, adapter_device2):
    if adapter_device1.get('plugin_name') == 'csv_adapter' and adapter_device2.get('plugin_name') == 'esx_adapter':
        return True
    if adapter_device2.get('plugin_name') == 'csv_adapter' and adapter_device1.get('plugin_name') == 'esx_adapter':
        return True
    return False


class StaticCorrelatorEngine(CorrelatorEngineBase):
    """
    For efficiency reasons this engine assumes a different structure (let's refer to it as compact structure)
    of axonius devices.
    Each adapter device should have
    {
        plugin_name: "",
        plugin_unique_name: "",
        data: {
            id: "",
            OS: {
                type: "",
                whatever...
            },
            hostname: "",
            network_interfaces: [
                {
                    IP: ["127.0.0.1", ...],
                    whatever...
                },
                ...
            ]
        }
    }
    """
    @property
    def _correlation_preconditions(self):
        # this is the least of all acceptable preconditions for correlatable devices - if none is satisfied there's no
        # way to correlate the devices and so it won't be added to adapters_to_correlate
        return [has_hostname, has_name, has_mac, has_serial, has_cloud_id, has_ad_or_azure_name, has_last_used_users,
                has_nessus_scan_no_id, has_resource_id, has_public_ips]

    def _correlate_gce_chef(self, adapters_to_correlate):
        logger.info('Starting to correlate GCE')
        filtered_adapters_list = filter(get_asset_gce_chef, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_gce_chef],
                                      [compare_asset_gce_chef],
                                      [],
                                      [ips_do_not_contradict],
                                      {'Reason': 'They have the same GCE-CHEF name'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_fw_ip(self, adapters_to_correlate):
        logger.info('Starting to correlate fw ip')
        filtered_adapters_list = filter(get_fw_ip, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_fw_ip],
                                      [comapre_fw_ip],
                                      [],
                                      [],
                                      {'Reason': 'They have the same host fw ip'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_host_serial_g(self, adapters_to_correlate):
        logger.info('Starting to correlate host serial g')
        filtered_adapters_list = filter(get_host_serial_g, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_host_serial_g],
                                      [compare_host_serial_g],
                                      [is_snow_adapter],
                                      [one_is_not_snow],
                                      {'Reason': 'They have the same host serail with g'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_v_dash_name(self, adapters_to_correlate):
        logger.info('Starting to correlate v dash name')
        filtered_adapters_list = filter(get_v_dash_name, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_v_dash_name],
                                      [compare_v_dash_name],
                                      [is_snow_adapter],
                                      [one_is_not_snow],
                                      {'Reason': 'They have the same host without v dash'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_cp_esx_csv(self, adapters_to_correlate):
        logger.info('Starting to cp esx csv')
        filtered_adapters_list = filter(get_cp_esx_csv, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_cp_esx_csv],
                                      [compare_cp_esx_csv],
                                      [],
                                      [esx_and_csv],
                                      {'Reason': 'They have the cp esx csv'},
                                      CorrelationReason.StaticAnalysis)

    def _corelate_ec2_id_route53(self, adapters_to_correlate):
        logger.info('Starting to ec2_id_route53')
        filtered_adapters_list = filter(get_ec2_id_route53, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_ec2_id_route53],
                                      [compare_ec2_id_route53],
                                      [],
                                      [],
                                      {'Reason': 'They have same ec2 route 53 i-id'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_alias_hostname(self, adapters_to_correlate):
        logger.info('Starting to alias snow hostname')
        filtered_adapters_list = filter(get_alias_name, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_alias_name],
                                      [compare_alias_name],
                                      [is_snow_adapter],
                                      [one_is_not_snow],
                                      {'Reason': 'They have the same alias-hostname'},
                                      CorrelationReason.StaticAnalysis)

    # pylint: disable=R0912,too-many-boolean-expressions
    def _correlate_mac(self, adapters_to_correlate, correlate_by_snow_mac):
        """
        To write a correlator rule we do a few things:
        1.  list(filtered_adapters_list) -
                filter in only adapters we can actually later correlate - for example here we can only correlate
                adapters with mac, ip and os - having already normalized them we can use the normalized field for
                efficiency

        2.  [get_os_type] - since the first comparison is pairwise we want to sort according to something we can decide
                between to adapters whether they share it or not just using sorting - i.e. not lists or sets. The great
                thing here is every parameter we can use would decrease the number of permutations by a huge factor.

        3.  [compare_os_type] - this is the respective list of comparators for the sorting lambdas, in this case since
                the only way to sort was os type (as mac and ip are both sets) we only compare the os before inserting
                into the bucket

        4.  [is_different_plugin, compare_macs, _compare_ips] - the list of comparators to use on a pair from the
                bucket - a pair that has made it through this list is considered a correlation so choose wisely!

        5.  {'Reason': 'They have the same MAC and IPs don\'t contradict'} - the reason for the correlation -
                try to make it as descriptive as possible please

        6. CorrelationReason.StaticAnalysis - the analysis used to discover the correlation
        """

        logger.info('Starting to correlate on MAC')
        mac_indexed = {}

        filtered_adapters_list = filter(not_saltstack_enterprise_linux, adapters_to_correlate)
        filtered_adapters_list = filter(not_lansweeper_assetname_no_hostname, filtered_adapters_list)
        if not correlate_by_snow_mac:
            filtered_adapters_list = filter(lambda adap: not is_snow_adapter(adap), filtered_adapters_list)

        filtered_adapters_list = filter(lambda adap: not is_claroty_ten_adapter_more_mac(adap), filtered_adapters_list)
        filtered_adapters_list = filter(lambda adap: not is_esx_and_hostname_more_mac(adap), filtered_adapters_list)

        allow_old_mac_list = ALLOW_OLD_MAC_LIST

        if correlate_by_snow_mac:
            allow_old_mac_list.extend(['service_now_adapter', 'service_now_sql_adapter', 'service_now_akana_adapter'])

        for adapter in filtered_adapters_list:
            # Don't add to the MAC comparisons devices that haven't seen for more than 30 days
            if is_old_device(adapter, number_of_days=5) and adapter.get('plugin_name') not in allow_old_mac_list:
                continue
            macs = adapter.get(NORMALIZED_MACS)
            if macs:
                for mac in macs:
                    if mac and mac != '000000000000':
                        mac_indexed.setdefault(mac, []).append(adapter)

        # find contradicting hostnames with the same mac to eliminate macs.
        # Also using predefined blacklist of known macs.
        mac_blacklist = set()
        mac_blacklist = mac_blacklist.union(ALL_BLACKLIST)
        for mac, matches in mac_indexed.items():
            found_reg_mac = False
            for reg_mac in FROM_FIELDS_BLACK_LIST_REG:
                if compare_reg_mac(reg_mac, mac):
                    mac_blacklist.add(mac)
                    found_reg_mac = True
                    break
            if found_reg_mac:
                continue
            for x, y in combinations(matches, 2):
                if not hostnames_do_not_contradict(x, y):
                    if mac not in mac_blacklist:
                        logger.debug(f'This could be bad mac {mac}')
                        mac_manufacturer = get_manufacturer_from_mac(mac)
                        if not mac_manufacturer:
                            mac_manufacturer = ''
                        # pylint: disable=line-too-long
                        if not (is_different_plugin(x, y) or force_mac_adapters(x))\
                                or (get_domain_for_correlation(x) and get_domain_for_correlation(y) and is_windows(x) and is_windows(y) and compare_domain_for_correlation(x, y)) \
                                or x.get('plugin_name') in DANGEROUS_ADAPTERS \
                                or y.get('plugin_name') in DANGEROUS_ADAPTERS \
                                or (x.get('plugin_name') in SEMI_DANGEROUS_ADAPTERS and y.get('plugin_name') in SEMI_DANGEROUS_ADAPTERS) \
                                or cb_defense_basic_id_condradict(x, y) \
                                or 'vmware' in mac_manufacturer.lower() \
                                or mac_manufacturer in ['(Realtek (UpTech? also reported))'] \
                                or not cloud_id_do_not_contradict(x, y) \
                                or not serials_do_not_contradict(x, y):
                            logger.debug(f'Added to blacklist {mac} for X {x} and Y {y}')
                            mac_blacklist.add(mac)
                            break

        for mac in mac_blacklist:
            if mac in mac_indexed:
                del mac_indexed[mac]

        for mac, matches in mac_indexed.items():
            if 30 >= len(matches) >= 2:
                inner_compare_funcs = [compare_macs_or_one_is_jamf]
                mac_manufacturer = None
                try:
                    mac_manufacturer = get_manufacturer_from_mac(mac)
                except Exception:
                    pass
                # pylint: disable=line-too-long
                if not mac_manufacturer or ('cisco systems' not in mac_manufacturer.lower() and 'juniper networks' not in mac_manufacturer.lower()):
                    inner_compare_funcs.append(if_soalrwinds_compare_all)
                yield from self._bucket_correlate(matches,
                                                  [],
                                                  [],
                                                  [],
                                                  inner_compare_funcs,
                                                  {'Reason': 'They have the same MAC'},
                                                  CorrelationReason.StaticAnalysis)

    def _correlate_imei_serial(self, adapters_to_correlate):
        logger.info('Starting to correlate imei serial')
        filtered_adapters_list = filter(get_imei_or_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_imei_or_serial],
                                      [compare_imei_or_serial],
                                      [get_imei],
                                      [],
                                      {'Reason': 'They have the same imei and serail'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_snow_asset_host_snow_no_dash(self, adapters_to_correlate):
        logger.info('Starting to correlate asset host snow no dash')
        filtered_adapters_list = filter(get_asset_or_host_no_dash, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_or_host_no_dash],
                                      [compare_asset_hosts_no_dash],
                                      [is_snow_netgear_adapter],
                                      [],
                                      {'Reason': 'They have the same asset host before dash and one from snow'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_snow_host_asset_snow_no_dash(self, adapters_to_correlate):
        logger.info('Starting to correlate host asset snow no dash')
        filtered_adapters_list = filter(get_host_or_asset_no_dash, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_host_or_asset_no_dash],
                                      [compare_host_or_asset_no_dash],
                                      [is_snow_netgear_adapter],
                                      [],
                                      {'Reason': 'They have the same host asset before dash and one from snow'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_hostname_fqdn_ip(self, adapters_to_correlate):
        logger.info('Starting to correlate on Hostname_FQDN-IP')
        filtered_adapters_list = filter(get_fqdn_or_hostname,
                                        filter(get_normalized_ip, adapters_to_correlate))
        filtered_adapters_list = filter(igar_with_no_serial, filtered_adapters_list)
        filtered_adapters_list = filter(remove_qualys_no_mac_with_cloud_id, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_fqdn_or_hostname],
                                      [compare_fqdn_or_hostname],
                                      [],
                                      [ips_do_not_contradict_or_mac_intersection, macs_do_not_contradict,
                                       not_wifi_adapters, agent_uuid_do_not_contradict, customer_do_not_contradict,
                                       cloud_id_do_not_contradict, serials_do_not_contradict],
                                      {'Reason': 'They have the same hostname_fqdn and IPs or MACs'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_hostname_ip(self, adapters_to_correlate):
        logger.info('Starting to correlate on Hostname-IP')
        filtered_adapters_list = filter(get_normalized_hostname_str,
                                        filter(get_normalized_ip, adapters_to_correlate))
        filtered_adapters_list = filter(igar_with_no_serial, filtered_adapters_list)
        filtered_adapters_list = filter(remove_qualys_no_mac_with_cloud_id, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_normalized_hostname_str],
                                      [compare_device_normalized_hostname],
                                      [],
                                      [macs_do_not_contradict, ips_do_not_contradict_or_mac_intersection,
                                       not_wifi_adapters, agent_uuid_do_not_contradict, customer_do_not_contradict,
                                       cloud_id_do_not_contradict, serials_do_not_contradict],
                                      {'Reason': 'They have the same hostname and IPs or MACs'},
                                      CorrelationReason.StaticAnalysis)

    def _correlat_junos_solar_ips_hostname(self, adapters_to_correlate):
        logger.info('Starting to correlate on Solarwinds Junos IP')
        filtered_adapters_list = filter(is_solarwinds_node_or_junos_basic, adapters_to_correlate)
        filtered_adapters_list = filter(get_solarwinds_ip_or_hostname, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_solarwinds_ip_or_hostname],
                                      [compare_solarwinds_ip_or_hostname],
                                      [not_solarwinds_node],
                                      [],
                                      {'Reason': 'Solarwinds Junos Ips'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_hostname_user(self, adapters_to_correlate):
        logger.info('Starting to correlate on Hostname-LastUsedUser')
        filtered_adapters_list = filter(get_normalized_hostname_str,
                                        filter(get_last_used_users, adapters_to_correlate))
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_normalized_hostname_str],
                                      [compare_device_normalized_hostname],
                                      [lambda x: x.get('plugin_name') in USERS_CORRELATION_ADAPTERS],
                                      [compare_last_used_users,
                                       not_wifi_adapters, agent_uuid_do_not_contradict,
                                       serials_do_not_contradict],
                                      {'Reason': 'They have the same hostname and LastUsedUser'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_hostname_domain(self, adapters_to_correlate):
        logger.info('Starting to correlate on Hostname-Domain')
        filtered_adapters_list = filter(get_asset_or_host, filter(get_domain_for_correlation,
                                                                  adapters_to_correlate))
        filtered_adapters_list = filter(hostname_not_problematic, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_or_host],
                                      [compare_asset_hosts],
                                      [is_from_ad],
                                      [compare_domain_for_correlation,
                                       not_wifi_adapters, agent_uuid_do_not_contradict,
                                       serials_do_not_contradict],
                                      {'Reason': 'They have the same hostname and domain'},
                                      CorrelationReason.StaticAnalysis)

    # pylint: disable=invalid-name
    def _correlate_hostname_only_host_adapter(self, adapters_to_correlate, csv_full_hostname,
                                              allow_global_hostname_correlation):
        logger.info('Starting to correlate on Hostname-only')
        filtered_adapters_list = filter(get_normalized_hostname_str, adapters_to_correlate)
        # pylint: disable=line-too-long
        filtered_adapters_list = filter(hostname_not_problematic, filtered_adapters_list)
        filtered_adapters_list = filter(not_wifi_adapter, filtered_adapters_list)
        filtered_adapters_list = filter(lambda x: x.get('plugin_name') != 'cisco_meraki_adapter',
                                        filtered_adapters_list)
        inner_compare = [serials_do_not_contradict, agent_uuid_do_not_contradict, os_do_not_contradict]
        if csv_full_hostname:
            inner_compare.append(compare_hostname)
        else:
            inner_compare.append(if_csv_compare_full_path)
        if allow_global_hostname_correlation:
            one_pair = []
        else:
            one_pair = [is_only_host_adapter_or_host_only_force]
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_normalized_hostname_str],
                                      [compare_device_normalized_hostname],
                                      one_pair,
                                      inner_compare,
                                      {'Reason': 'They have the same hostname and from specifc adapters'},
                                      CorrelationReason.StaticAnalysis)

    # pylint: enable=invalid-name
    def _correlate_serial(self, adapters_to_correlate):
        logger.info('Starting to correlate on Serial')
        filtered_adapters_list = filter(get_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_serial],
                                      [lambda a, b: a['data']['device_serial'].upper() == b['data'][
                                          'device_serial'].upper()],
                                      [],
                                      [asset_hostnames_do_not_contradict],
                                      {'Reason': 'They have the same serial'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_serial_no_s(self, adapters_to_correlate):
        logger.info('Starting to correlate on Serial no s')
        filtered_adapters_list = filter(get_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_serial_no_s],
                                      [compare_serial_no_s],
                                      [],
                                      [asset_hostnames_do_not_contradict],
                                      {'Reason': 'They have the same serial even with S at the beginning'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_nessus_no_scan_id(self, adapters_to_correlate):
        logger.info('Starting to correlate on nessus id')
        filtered_adapters_list = filter(get_nessus_no_scan_id, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_nessus_no_scan_id],
                                      [compare_nessus_no_scan_id],
                                      [],
                                      [asset_hostnames_do_not_contradict],
                                      {'Reason': 'They are the same nessus id no scan'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_private_dns_hostname_prefix(self, adapters_to_correlate):
        logger.info('Starting to correlate on private dns hostname prefix')
        filtered_adapters_list = filter(get_prefix_private_dns_or_hostname, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_prefix_private_dns_or_hostname],
                                      [compare_hostname_or_private_dns],
                                      [get_private_dns_name],
                                      [ips_do_not_contradict_or_mac_intersection],
                                      {'Reason': 'They are the same nprivate dns hostname prefix'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_cloud_instances(self, adapters_to_correlate):
        logger.info('Starting to correlate on Cloud Instances')
        filtered_adapters_list = filter(get_cloud_data, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_cloud_data],
                                      [compare_clouds],
                                      [],
                                      [customer_do_not_contradict],
                                      {'Reason': 'They are the same cloud instance'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_serial_with_bios_serial(self, adapters_to_correlate):
        logger.info('Starting to correlate on Bios Serial')
        filtered_adapters_list = filter(get_bios_serial_or_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_bios_serial_or_serial],
                                      [compare_bios_serial_serial],
                                      [],
                                      [asset_hostnames_do_not_contradict],
                                      {'Reason': 'Bios serial or serials are equal'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_serial_with_hostname(self, adapters_to_correlate):
        # Right now we do it only with Airwatch
        logger.info('Starting to correlate on Hostname-Serial')
        filtered_adapters_list = filter(get_hostname_or_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_hostname_or_serial],
                                      [compare_hostname_serial],
                                      [lambda x: x.get('plugin_name') in ['airwatch_adapter', 'jumpcloud_adapter']],
                                      [asset_hostnames_do_not_contradict, ips_do_not_contradict_or_mac_intersection],
                                      {'Reason': 'Hostname or serials are equal'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_serial_with_bios_serial_no_s(self, adapters_to_correlate):
        logger.info('Starting to correlate on Bios Serial No S')
        filtered_adapters_list = filter(get_bios_serial_or_serial, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_bios_serial_or_serial_no_s],
                                      [compare_bios_serial_serial_no_s],
                                      [],
                                      [asset_hostnames_do_not_contradict],
                                      {'Reason': 'Bios serial or serials are equal with no S'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_with_ad(self, adapters_to_correlate):
        """
        AD correlation is a little more loose - we allow correlation based on hostname alone.
        In order to lower the false positive rate we don't use the normalized hostname but rather the full one
        """
        logger.info('Starting to correlate on Hostname-(FULL HOSTNAME)')
        filtered_adapters_list = filter(get_hostname_no_localhost, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_hostname],
                                      [compare_hostname],
                                      [is_full_hostname_adapter],
                                      [not_wifi_adapters],
                                      {'Reason': 'They have the same FULL hostname'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_with_twistlock(self, adapters_to_correlate):
        """
        AD correlation is a little more loose - we allow correlation based on hostname alone.
        In order to lower the false positive rate we don't use the normalized hostname but rather the full one
        """
        logger.info('Starting to correlate on Twistlock')
        filtered_adapters_list = filter(is_from_twistlock_or_cloud,
                                        filter(get_host_or_asset_full, adapters_to_correlate))
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_host_or_asset_full],
                                      [compare_hosts_asset_full],
                                      [is_from_twistlock],
                                      [],
                                      {'Reason': 'They have the same hostname are twistlock'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_with_digicert_pki(self, adapters_to_correlate):
        logger.info('Starting to correlate on Digicert pki')
        filtered_adapters_list = filter(get_asset_or_host_full, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_or_host_full],
                                      [compare_asset_hosts_full],
                                      [is_from_digicert_pki],
                                      [],
                                      {'Reason': 'They have the same hostname and one is digicert PKI'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_with_juniper(self, adapters_to_correlate):
        """
        juniper correlation is a little more loose - we allow correlation based on asset name alone,
        """
        logger.info('Starting to correlate on asset-name juniper')
        filtered_adapters_list = filter(is_from_juniper_and_asset_name, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_name],
                                      [compare_asset_name],
                                      [is_junos_space_device],
                                      [],
                                      {'Reason': 'Juniper devices with same asset name'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_deep_tenable_aws_id(self, adapters_to_correlate):
        logger.info(f'Starting to correlate on deep-tenable_io aws is')
        filtered_adapters_list = filter(is_from_deeps_tenable_io_or_aws, adapters_to_correlate)
        filtered_adapters_list = filter(get_cloud_id_or_hostname, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_cloud_id_or_hostname],
                                      [compare_cloud_id_or_hostname],
                                      [lambda x: x.get('plugin_name') == 'aws_adapter'],
                                      [],
                                      {'Reason': 'Cloud ID and Hostname are the same'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_aws_route53_dns_names(self, adapters_to_correlate):
        logger.info(f'Starting to correlate on dns_names')
        filtered_adapters_list = filter(lambda x: x.get('plugin_name') == 'aws_adapter', adapters_to_correlate)
        filtered_adapters_list = filter(get_dns_names, filtered_adapters_list)

        adapters_to_correlate_by_dns_name = defaultdict(list)
        for adapter_to_correlate in list(filtered_adapters_list):
            for dns_name_candidate in (adapter_to_correlate['data'].get('dns_names') or []):
                adapters_to_correlate_by_dns_name[dns_name_candidate].append(adapter_to_correlate)

        for adapters_to_correlate_buckets in adapters_to_correlate_by_dns_name.values():
            yield from self._bucket_correlate(adapters_to_correlate_buckets,
                                              [],
                                              [],
                                              [lambda x: x['data'].get('aws_device_type') == 'Route53'],
                                              [],
                                              {'Reason': 'AWS DNS Names are the same'},
                                              CorrelationReason.StaticAnalysis)

    def _correlate_ad_sccm_id(self, adapters_to_correlate):
        """
        We want to get all the devices with hostname (to reduce amount),
         then check if one adapter is SCCM and one is AD and to compare their ID
        """
        logger.info('Starting to correlate on SCCM-AD')
        filtered_adapters_list = filter(is_sccm_or_ad, adapters_to_correlate)
        filtered_adapters_list = filter(is_windows, filtered_adapters_list)
        filtered_adapters_list = filter(get_dst_name, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_dst_name],
                                      [compare_dst_name],
                                      [],
                                      [],
                                      {'Reason': 'They have the same ID and one is AD and the second is SCCM'},
                                      CorrelationReason.StaticAnalysis)

    def _correlata_azure_ad_intune(self, adapters_to_correlate):
        logger.info('Starting to correlate on Intune Azuze ad')
        filtered_adapters_list = filter(get_azure_ad_id, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_azure_ad_id],
                                      [compare_azure_ad_id],
                                      [lambda x: x['data'].get('azure_ad_id')],
                                      [host_asset_azure_ad_do_not_contradict],
                                      {'Reason': 'They have the same AZURE AD ID'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_ad_azure_ad(self, adapters_to_correlate):
        """
        Correlate Azure AD and AD
        """
        logger.info('Starting to correlate on AD-AzureAD')
        filtered_adapters_list = filter(is_azuread_or_ad_and_have_name, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_ad_name_or_azure_display_name],
                                      [compare_ad_name_or_azure_display_name],
                                      [is_from_ad],
                                      [domain_do_not_contradict, hostnames_do_not_contradict,
                                       host_asset_azure_ad_do_not_contradict],
                                      {'Reason': 'They have the same display name'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_asset_host(self, adapters_to_correlate, correlate_azure_ad_name_only):
        """
        Correlating by asset first + IP
        :param adapters_to_correlate:
        :return:
        """
        logger.info('Starting to correlate on Asset-Host')
        filtered_adapters_list = filter(get_asset_or_host, adapters_to_correlate)
        filtered_adapters_list = filter(igar_with_no_serial, filtered_adapters_list)
        filtered_adapters_list = filter(remove_qualys_no_mac_with_cloud_id, filtered_adapters_list)
        inner_rules = [not_wifi_adapters, macs_do_not_contradict,
                       asset_hostnames_do_not_contradict_and_no_chef,
                       serials_do_not_contradict]
        if not correlate_azure_ad_name_only:
            inner_rules.append(ips_do_not_contradict_or_mac_intersection_or_asset_only_adapter)
        else:
            inner_rules.append(ips_do_not_contradict_or_mac_intersection_or_asset_only_adapter_and_azure_ad)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_or_host],
                                      [compare_asset_hosts],
                                      [get_asset_name],
                                      inner_rules,
                                      {'Reason': 'They have the same Asset name'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_asset_host_email(self, adapters_to_correlate):
        """
        Correlating by asset first + IP
        :param adapters_to_correlate:
        :return:
        """
        logger.info('Starting to correlate on Asset-Host Email')
        filtered_adapters_list = filter(get_asset_or_host, adapters_to_correlate)
        filtered_adapters_list = filter(igar_with_no_serial, filtered_adapters_list)
        filtered_adapters_list = filter(remove_qualys_no_mac_with_cloud_id, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_or_host],
                                      [compare_asset_hosts],
                                      [get_asset_name],
                                      [compare_emails, macs_do_not_contradict,
                                       not_wifi_adapters,
                                       asset_hostnames_do_not_contradict_and_no_chef,
                                       serials_do_not_contradict],
                                      {'Reason': 'They have the same Asset name and EMAIL'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_asset_snow_host(self, adapters_to_correlate):
        """
        Correlating by asset first + IP
        :param adapters_to_correlate:
        :return:
        """
        logger.info('Starting to correlate on snowAsset-Host')
        filtered_adapters_list = filter(get_asset_snow_or_host, filter(get_normalized_ip, adapters_to_correlate))
        filtered_adapters_list = filter(igar_with_no_serial, filtered_adapters_list)
        filtered_adapters_list = filter(remove_qualys_no_mac_with_cloud_id, filtered_adapters_list)

        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_asset_snow_or_host],
                                      [compare_snow_asset_hosts],
                                      [is_asset_before_host_device],
                                      [ips_do_not_contradict_or_mac_intersection,
                                       not_wifi_adapters, macs_do_not_contradict,
                                       cloud_id_do_not_contradict,
                                       asset_hostnames_do_not_contradict_and_no_chef,
                                       serials_do_not_contradict],
                                      {'Reason': 'They have the same SNOW Asset + Hostname name'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_uuid(self, adapters_to_correlate):
        logger.info('Starting to correlate UUID')
        filtered_adapters_list = filter(get_uuid, adapters_to_correlate)
        filtered_adapters_list = filter(is_uuid_adapters, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_uuid],
                                      [compare_uuid],
                                      [],
                                      [hostnames_do_not_contradict],
                                      {'Reason': 'They have the same UUID'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_splunk_vpn_hostname(self, adapters_to_correlate):
        logger.info('Starting to correlate on Splunk VPN')
        filtered_adapters_list = filter(is_splunk_vpn, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_normalized_hostname_str],
                                      [compare_device_normalized_hostname],
                                      [],
                                      [],
                                      {'Reason': 'They have the same Normalized hostname and both are Splunk VPN'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_scep_sccm(self, adapters_to_correlate):
        logger.info('Starting to correlate SCEP SCCM')
        filtered_adapters_list = filter(get_resource_id, adapters_to_correlate)
        filtered_adapters_list = filter(get_sccm_server, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_resource_id],
                                      [compare_resource_id],
                                      [],
                                      [compare_sccm_server,
                                       asset_hostnames_do_not_contradict,
                                       ips_do_not_contradict_or_mac_intersection],
                                      {'Reason': 'They have the same resource ID plus SCCM SERVER'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_friendly_ad_name(self, adapters_to_correlate):
        logger.info('Starting to correlate friendly name and ad name')
        filtered_adapters_list = filter(friendly_name_or_ad_name, adapters_to_correlate)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [friendly_name_or_ad_name],
                                      [compare_friendly_ad_name],
                                      [],
                                      [one_is_ad_one_is_airwatch],
                                      {'Reason': 'They have the friendly and AD name the saem'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_one_public_ip(self, adapters_to_correlate):
        logger.info('Starting to correlate public ip')
        filtered_adapters_list = filter(get_one_public_ip, adapters_to_correlate)
        filtered_adapters_list = filter(is_public_ip_correlation_adapter, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_one_public_ip],
                                      [compare_one_public_ip],
                                      [],
                                      [],
                                      {'Reason': 'They have the same public ip'},
                                      CorrelationReason.StaticAnalysis)

    def _correlate_agent_uuid(self, adapters_to_correlate):
        logger.info('Starting to correlate Agent UUID')
        filtered_adapters_list = filter(get_agent_uuid, adapters_to_correlate)
        filtered_adapters_list = filter(get_hostname, filtered_adapters_list)
        return self._bucket_correlate(list(filtered_adapters_list),
                                      [get_agent_uuid],
                                      [compare_agent_uuids],
                                      [],
                                      [hostnames_do_not_contradict_or_tenable_io],
                                      {'Reason': 'They have the same Agent UUID'},
                                      CorrelationReason.StaticAnalysis)

    @staticmethod
    def _get_serial_dups_igar(adapters_to_correlate):
        dups_list = set()
        serial_dict = {}
        for adapter_device in adapters_to_correlate:
            if adapter_device.get('plugin_name') != 'igar_adapter':
                continue
            serial = get_serial(adapter_device)
            hostname = get_hostname(adapter_device)
            if not serial or not hostname:
                continue
            hostname = hostname.split('.')[0].lower()
            serial = serial.upper()
            if hostname not in serial_dict:
                serial_dict[hostname] = serial
            else:
                if serial != serial_dict[hostname]:
                    dups_list.add(hostname)
        return list(dups_list)

    def _raw_correlate(self, entities):
        # WARNING WARNING WARNING
        # Adding or changing any type of correlation here might require changing the appropriate logic
        # at static_correlator/service

        # since this operation is extremely costly, we normalize the adapter_devices:
        # 1. adding 2 fields to the root - NORMALIZED_IPS and NORMALIZED_MACS to allow easy access to the ips and macs
        #    of all the NICs
        # 2. uppering every field we might sort by - currently hostname and os type
        # 3. splitting the hostname into a list in order to be able to compare hostnames without depending on the domain
        _refresh_domain_to_dns_dict()
        _refresh_ad_client_count()
        correlate_snow_serial_only = bool(self._correlation_config and
                                          self._correlation_config.get('correlate_snow_serial_only') is True)
        adapters_to_correlate = list(normalize_adapter_devices(entities, correlate_snow_serial_only))
        global DUPLICATES_SERIALS_IGAR
        DUPLICATES_SERIALS_IGAR = self._get_serial_dups_igar(adapters_to_correlate)

        correlate_by_snow_mac = bool(self._correlation_config and
                                     self._correlation_config.get('correlate_by_snow_mac') is True)

        correlate_azure_ad_name_only = bool(self._correlation_config and
                                            self._correlation_config.get('correlate_azure_ad_name_only') is True)
        correlate_public_ip_only = bool(self._correlation_config and
                                        self._correlation_config.get('correlate_public_ip_only') is True)
        global ALLOW_SERVICE_NOW_BY_NAME_ONLY
        ALLOW_SERVICE_NOW_BY_NAME_ONLY = (self._correlation_config and
                                          self._correlation_config.get('allow_service_now_by_name_only') is True)

        correlate_snow_no_dash = bool(self._correlation_config and
                                      self._correlation_config.get('correlate_snow_no_dash') is True)
        if correlate_snow_no_dash:
            yield from self._correlate_v_dash_name(adapters_to_correlate)
            yield from self._correlate_alias_hostname(adapters_to_correlate)
        yield from self._correlate_cp_esx_csv(adapters_to_correlate)
        yield from self._corelate_ec2_id_route53(adapters_to_correlate)

        # let's find devices by, hostname, and ip:
        yield from self._correlate_hostname_ip(adapters_to_correlate)
        yield from self._correlate_hostname_fqdn_ip(adapters_to_correlate)
        # for ad specifically we added the option to correlate on hostname basis alone (dns name with the domain)
        yield from self._correlate_with_ad(adapters_to_correlate)

        yield from self._correlate_hostname_domain(adapters_to_correlate)

        yield from self._correlate_hostname_user(adapters_to_correlate)

        yield from self._correlat_junos_solar_ips_hostname(adapters_to_correlate)

        csv_full_hostname = bool(self._correlation_config and
                                 self._correlation_config.get('csv_full_hostname') is True)
        allow_global_hostname_correlation = bool(self._correlation_config and
                                                 self._correlation_config.get('global_hostname_correlation') is True)
        yield from self._correlate_hostname_only_host_adapter(adapters_to_correlate, csv_full_hostname,
                                                              allow_global_hostname_correlation)

        # Correlating mac must happen after all the other correlations are DONE.
        # the actual linking is happend in _process_correlation_result in other thread,
        # so in order to solve the race condition we yield marker here and
        # wait for all correlation to end until the marker in _map_correlation
        yield CorrelationMarker()
        yield from self._correlate_imei_serial(adapters_to_correlate)
        yield from self._correlate_with_twistlock(adapters_to_correlate)

        yield from self._correlate_with_digicert_pki(adapters_to_correlate)

        # Find adapters that share the same cloud type and cloud id
        yield from self._correlate_cloud_instances(adapters_to_correlate)

        # Find SCCM or Ad adapters with the same ID
        if self._correlation_config and self._correlation_config.get('correlate_ad_sccm') is True:
            yield from self._correlate_ad_sccm_id(adapters_to_correlate)

        # Find azure ad and ad with the same display name
        yield from self._correlate_ad_azure_ad(adapters_to_correlate)

        yield from self._correlata_azure_ad_intune(adapters_to_correlate)

        # juniper correlation is a little more loose - we allow correlation based on asset name alone,
        yield from self._correlate_with_juniper(adapters_to_correlate)

        yield from self._correlate_asset_host(adapters_to_correlate, correlate_azure_ad_name_only)
        yield from self._correlate_asset_host_email(adapters_to_correlate)

        yield from self._correlate_asset_snow_host(adapters_to_correlate)

        yield from self._correlate_splunk_vpn_hostname(adapters_to_correlate)

        yield from self._correlate_serial(adapters_to_correlate)

        yield from self._correlate_serial_with_bios_serial(adapters_to_correlate)
        yield from self._correlate_serial_with_bios_serial_no_s(adapters_to_correlate)
        yield from self._correlate_serial_no_s(adapters_to_correlate)
        yield from self._correlate_serial_with_hostname(adapters_to_correlate)
        yield from self._correlate_nessus_no_scan_id(adapters_to_correlate)
        yield from self._correlate_uuid(adapters_to_correlate)
        yield from self._correlate_scep_sccm(adapters_to_correlate)
        yield from self._correlate_deep_tenable_aws_id(adapters_to_correlate)
        yield from self._correlate_agent_uuid(adapters_to_correlate)
        yield from self._correlate_friendly_ad_name(adapters_to_correlate)
        if correlate_public_ip_only:
            yield from self._correlate_one_public_ip(adapters_to_correlate)
        # Disable route53 correlation, because this usually correlates many instances of the same ELB
        # and we don't want these kind of correlations - they are not the same host.
        #
        # yield from self._correlate_aws_route53_dns_names(adapters_to_correlate)

        # Find adapters with the same serial
        # Now let's find devices by MAC, and IPs don't contradict (we allow empty)
        yield from self._correlate_mac(adapters_to_correlate, correlate_by_snow_mac)
        yield from self._correlate_host_serial_g(adapters_to_correlate)
        yield from self._correlate_fw_ip(adapters_to_correlate)
        yield from self._correlate_gce_chef(adapters_to_correlate)

    @staticmethod
    def _post_process(first_name, first_id, second_name, second_id, data, reason) -> bool:
        if reason == CorrelationReason.StaticAnalysis:
            if second_name == first_name:
                # this means that some logic in the correlator logic is wrong, because
                # such correlations should have reason == "Logic"
                logger.error(
                    f'{first_name} correlated to itself, id: \'{first_id}\' and \'{second_id}\' via static analysis')
                return False
        return True

    @staticmethod
    def _bigger_picture_decision(first_axonius_device, second_axonius_device,
                                 first_adapter_device, second_adapter_device) -> bool:
        # Don't correlate devices that have AD in them but are not correlated according to AD
        # AX-2107
        ad_in_first = any(x[PLUGIN_NAME] == ACTIVE_DIRECTORY_PLUGIN_NAME for x in first_axonius_device['adapters'])
        ad_in_second = any(x[PLUGIN_NAME] == ACTIVE_DIRECTORY_PLUGIN_NAME for x in second_axonius_device['adapters'])
        if ad_in_first and ad_in_second:
            if first_adapter_device[PLUGIN_NAME] != ACTIVE_DIRECTORY_PLUGIN_NAME or \
                    second_adapter_device[PLUGIN_NAME] != ACTIVE_DIRECTORY_PLUGIN_NAME:
                return False

        return True
