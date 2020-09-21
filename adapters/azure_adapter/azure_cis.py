"""
Azure Cis helpers
"""
# pylint: disable=too-many-branches, too-many-nested-blocks
import logging
from typing import List

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


def is_disk_encrypted(disk: dict) -> bool:
    # XXX Currently does not work! Requires getting full disk information
    # and searching by disk name.
    try:
        props = disk.get('properties') or {}
        enc = props.get('encryption') or {}
        encryption_settings = enc.get('type')
        if encryption_settings:
            return str(encryption_settings).lower() in [
                'encryptionatrestwithplatformkey', 'encryptionatrestwithcustomerkey'
            ]
        return None
    except Exception as e:
        logger.exception(f'Could not determine encryption status: {str(e)}')
        return None


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

    # section 7  - CURRENTLY DOES NOT WORK! NEEDS SEPARATE API CALLS.

    device_raw = device.get_raw()
    os_disk = device_raw.get('storage_profile', {}).get('os_disk')
    if is_disk_encrypted(os_disk) is False:
        device.add_azure_cis_incompliant_rule('7.1')
    for disk in device_raw.get('storage_profile', {}).get('data_disks', []):
        if is_disk_encrypted(disk) is False:
            device.add_azure_cis_incompliant_rule('7.2')
            break
