"""
Azure Cis helpers
"""
# pylint: disable=too-many-branches, too-many-nested-blocks
import logging
from typing import List, Optional

from axonius.clients.azure.structures import AzureAdapterEntity
from azure_adapter.structures import AzureDeviceInstance, AzureNetworkSecurityGroupRule

logger = logging.getLogger(f'axonius.{__name__}')

PORT_RDP = 3389
PORT_SSH = 22


def is_nsg_allow_inbound_internet(nsg_rule: AzureNetworkSecurityGroupRule, port: int) -> bool:
    """
    Check a nsg rule to see if a port is accessible from the internet
    :param nsg_rule: network security group rule to check
    :param port: port to check
    :return: True if port is not restricted from the internet
    """
    port_str = str(port)
    properties = nsg_rule.to_dict()
    if not properties:
        logger.debug(f'Empty nsg rule: {nsg_rule}')
        return False
    rule_access = str(properties.get('access')).lower()
    rule_direction = str(properties.get('direction')).lower()
    rule_protocol = str(properties.get('protocol')).lower()
    rule_destination_list = [str(x).lower() for x in properties.get('destination_port_ranges') or []]
    rule_source_address_list = [str(x).lower() for x in properties.get('source_address_prefixes') or []]

    rule_destination_match = False

    if rule_access == 'allow' and rule_direction == 'inbound' and rule_protocol in ['tcp', '*']:
        if '*' in rule_destination_list or port_str in rule_destination_list:
            rule_destination_match = True
        else:
            for rule_port_range in rule_destination_list:
                if '-' in rule_port_range:
                    try:
                        from_port, to_port = rule_port_range.split('-')
                        if int(from_port) <= port <= int(to_port):
                            rule_destination_match = True
                            break
                    except Exception:
                        logger.exception(f'Failed parsing port range {rule_port_range!r}')

        if rule_destination_match:
            all_destination_rules = rule_source_address_list
            return any(
                ('/0' in dest_rule or dest_rule in ['*', '0.0.0.0', 'internet', 'any'])
                for dest_rule in all_destination_rules
            )
    return False


def _check_inbound_nsg_list(device: AzureDeviceInstance,
                            nsg_list: List[AzureNetworkSecurityGroupRule],
                            rule_section: str,
                            port: int):
    for nsg_rule in nsg_list:
        if is_nsg_allow_inbound_internet(nsg_rule, port):
            device.add_azure_cis_incompliant_rule(rule_section)
            break


def is_disk_encrypted(disk_name: str, vm_instance_view: dict) -> Optional[bool]:
    if not (vm_instance_view and isinstance(vm_instance_view, dict)):
        return None  # None value means we couldn't get information.
    disks = vm_instance_view.get('disks') or []
    if not (disks and isinstance(disks, list)):
        return None
    for disk in disks:
        if not (disk and isinstance(disk, dict)):
            continue
        name = disk.get('name')
        if not name == disk_name:
            continue
        encryption_settings = disk.get('encryption_settings') or []
        if not (encryption_settings and isinstance(encryption_settings, list)):
            return False  # If no encryption settings, disk is not encrypted
        for enc_entry in encryption_settings:
            if not isinstance(enc_entry, dict):
                continue
            if enc_entry.get('enabled') is True:
                return True  # If even one setting is enabled, disk is encrypted
    # If we got here then this disk either has no encryption settings, or they exist but are not enabled.
    # Meaning, disk is not encrypted - so return False.
    return False


def append_azure_cis_data_to_user(user: AzureAdapterEntity):
    """
    XXX Azure adapter does not fetch users
    :param user: AzureAdAdapter.MyUserAdapter instance
    """
    return


def append_azure_cis_data_to_device(device: AzureAdapterEntity):
    """
    Add CIS rule incompliances to Azure VM instances:
    6.1 rdp from internet
    6.2 ssh from internet
    7.1 os disk encryption  XXX NOT WORKING YET - NEEDS CHANGES IN ADAPTER
    7.2 data disks encryption XXX NOT WORKING YET - NEEDS CHANGES IN ADAPTER
    :param device: Azure VM instance
    """
    # section 6
    nsg_list = device.get_field_safe('azure_firewall_rules')
    if nsg_list and isinstance(nsg_list, list):
        _check_inbound_nsg_list(device, nsg_list, '6.1', PORT_RDP)
        _check_inbound_nsg_list(device, nsg_list, '6.2', PORT_SSH)

    device_raw = device.get_raw()

    instance_view = device_raw.get('instance_view')

    os_disk = device_raw.get('storage_profile', {}).get('os_disk')
    os_disk_name = os_disk.get('name')
    if is_disk_encrypted(os_disk_name, instance_view) is False:
        device.add_azure_cis_incompliant_rule('7.1')
    for disk in device_raw.get('storage_profile', {}).get('data_disks', []):
        disk_name = disk.get('name')
        if is_disk_encrypted(disk_name, instance_view) is False:
            device.add_azure_cis_incompliant_rule('7.2')
            break
